"""Tests de `veille` : PowerShell et `gh` sont SIMULÉS, aucun appel réel, aucun fichier réel de donnees/.

Garde-fou : tout appel réel (`veille.executer_powershell`, `kanban.executer_gh`, `subprocess.run`) lève `AppelReel`,
une BaseException exprès pour qu'un `except Exception` du code testé ne l'avale pas. Les fichiers d'entrée vivent
dans des dossiers temporaires. Les données sont fictives.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

import commun
import kanban
import veille

EXECUTEUR_POWERSHELL_REEL = veille.executer_powershell  # gardé pour tester son appel (subprocess simulé)
RACINE_DEPOT = Path(__file__).resolve().parent.parent

MAINT = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
FUSEAU = timezone(timedelta(hours=2))  # heure locale = 14:00 pour MAINT
KANBAN = {"numero": 1, "proprietaire": "@me"}


class AppelReel(BaseException):
    pass


@pytest.fixture(autouse=True)
def aucun_appel_reel(monkeypatch):
    def interdit(*_a, **_k):
        raise AppelReel("appel réel pendant un test")

    monkeypatch.setattr(kanban, "executer_gh", interdit)
    monkeypatch.setattr(veille, "executer_powershell", interdit)
    monkeypatch.setattr(subprocess, "run", interdit)


# ---------- faux et fabriques ----------
def sec(dt: datetime) -> int:
    return int(dt.timestamp())


def tache(nom, etat="Ready", dernier=MAINT - timedelta(minutes=5), resultat=0, prochain=None):
    return {
        "Nom": nom,
        "State": etat,
        "LastRun": sec(dernier) if dernier else None,
        "LastResult": resultat,
        "NextRun": sec(prochain) if prochain else None,
    }


def faux_ps(*entrees, code=0):
    def executer(script):
        executer.scripts.append(script)
        return code, json.dumps(list(entrees))

    executer.scripts = []
    return executer


def faux_gh(cartes):
    return lambda args: kanban.Resultat(0, json.dumps({"totalCount": len(cartes), "items": cartes}))


def carte(titre, statut="En cours", nature="Chantier"):
    return {"title": titre, "status": statut, "nature": nature}


def config(nom="T", periode=15, facteur=4, fenetre=None, carte=None, projet="demo"):
    return {
        "nom": nom,
        "projet": projet,
        "periode_min": periode,
        "retard_facteur": facteur,
        "fenetre": fenetre,
        "carte": carte,
    }


def dossier(tmp_path, taches=None, echeances=(), journal=(), brut=None):
    """Dossier `donnees/` temporaire ; `brut` remplace un fichier par son contenu texte."""
    contenus = {
        "veille-taches.json": json.dumps({"taches": taches if taches is not None else []}),
        "echeances.json": json.dumps(list(echeances)),
        "missions.jsonl": "\n".join(json.dumps(x) for x in journal) + "\n",
    }
    contenus.update(brut or {})
    tmp_path.mkdir(parents=True, exist_ok=True)
    for nom, texte in contenus.items():
        (tmp_path / nom).write_text(texte, encoding="utf-8")
    return tmp_path


def lancer(tmp_path, ps=None, gh=None, maintenant=MAINT, kanban_cfg=KANBAN, windows=True, **fichiers):
    d = dossier(tmp_path, **fichiers)
    return veille.analyser(
        d, maintenant, ps or faux_ps(), gh or faux_gh([]), FUSEAU, config_kanban=kanban_cfg, windows=windows
    )


def cles(rapport):
    return [a["cle"] for a in rapport["alertes"]]


def alerte(rapport, cle):
    trouvees = [a for a in rapport["alertes"] if a["cle"] == cle]
    assert len(trouvees) == 1, (cle, cles(rapport))
    return trouvees[0]


# ---------- tâches Windows ----------
def test_tache_en_echec_est_critique(tmp_path):
    r = lancer(tmp_path, ps=faux_ps(tache("T", resultat=1)), taches=[config()])
    a = alerte(r, "tache:T:echec")
    assert a["niveau"] == "critique" and "0x1" in a["detail"]


@pytest.mark.parametrize("resultat", [0, 267009, 267010, 267011, None])
def test_codes_qui_ne_sont_pas_des_echecs(tmp_path, resultat):
    r = lancer(tmp_path, ps=faux_ps(tache("T", resultat=resultat)), taches=[config()])
    assert "tache:T:echec" not in cles(r)


def test_silencieuse_au_dela_de_periode_fois_facteur(tmp_path):
    seuil = 15 * 4
    juste = tache("T", dernier=MAINT - timedelta(minutes=seuil))
    trop = tache("T", dernier=MAINT - timedelta(minutes=seuil + 1))
    assert "tache:T:silencieuse" not in cles(lancer(tmp_path / "a", ps=faux_ps(juste), taches=[config()]))
    assert (
        alerte(lancer(tmp_path / "b", ps=faux_ps(trop), taches=[config()]), "tache:T:silencieuse")["niveau"]
        == "attention"
    )


def test_jamais_lancee_est_silencieuse(tmp_path):
    r = lancer(tmp_path, ps=faux_ps(tache("T", dernier=None)), taches=[config()])
    assert "Aucun passage" in alerte(r, "tache:T:silencieuse")["detail"]


def test_dernier_passage_1999_vaut_jamais_lance(tmp_path):
    r = lancer(tmp_path, ps=faux_ps(tache("T", dernier=datetime(1999, 11, 30, tzinfo=UTC))), taches=[config()])
    assert "tache:T:silencieuse" in cles(r)


def test_hors_fenetre_pas_d_alerte(tmp_path):
    vieux = tache("T", dernier=MAINT - timedelta(days=2))
    # 14 h locale : hors de la fenêtre [20, 23]
    assert cles(lancer(tmp_path, ps=faux_ps(vieux), taches=[config(fenetre=[20, 23])])) == []


def test_fenetre_ne_compte_que_les_heures_de_fenetre(tmp_path):
    # fenêtre 8-18 h, dernier passage hier 17 h locale : 1 h hier + 6 h aujourd'hui (8-14) = 7 h = 420 min
    local = datetime(2026, 11, 24, 17, 0, tzinfo=FUSEAU)
    t = tache("T", dernier=local)
    a = alerte(
        lancer(tmp_path, ps=faux_ps(t), taches=[config(periode=60, facteur=6, fenetre=[8, 18])]), "tache:T:silencieuse"
    )
    assert "7 h 00" in a["detail"] and "heures de la fenêtre" in a["detail"]


def test_minutes_en_fenetre_et_fenetre_qui_passe_minuit():
    debut, fin = datetime(2026, 11, 24, 17, 0), datetime(2026, 11, 25, 14, 0)
    assert veille.minutes_en_fenetre(debut, fin, [8, 18]) == 420
    # fenêtre 22 h - 6 h : 2 h (22-24) + 6 h (0-6) = 480 min entre 22 h le 24 et 14 h le 25
    assert veille.minutes_en_fenetre(datetime(2026, 11, 24, 22, 0), fin, [22, 6]) == 480


def test_desactivee_et_desactivee_volontairement(tmp_path):
    t = tache("T", etat="Disabled")
    assert (
        alerte(lancer(tmp_path / "a", ps=faux_ps(t), taches=[config()]), "tache:T:desactivee")["niveau"] == "attention"
    )
    voulue = {**config(), "desactivee_volontairement": True}
    r = lancer(tmp_path / "b", ps=faux_ps(t), taches=[voulue])
    assert cles(r) == [] and r["taches"][0]["ok"] is True
    reactivee = tache("T", etat="Ready", dernier=MAINT - timedelta(days=3))
    assert "tache:T:silencieuse" in cles(lancer(tmp_path / "c", ps=faux_ps(reactivee), taches=[voulue]))


def test_introuvable(tmp_path):
    r = lancer(tmp_path, ps=faux_ps(), taches=[config()])
    assert alerte(r, "tache:T:introuvable")["niveau"] == "attention" and r["taches"][0]["etat"] == "introuvable"


def test_nom_insensible_a_la_casse_et_un_seul_appel_powershell(tmp_path):
    ps = faux_ps(tache("PIPE-nuit"), tache("autre"))
    r = lancer(tmp_path, ps=ps, taches=[config("pipe-NUIT"), config("autre")])
    assert cles(r) == [] and len(ps.scripts) == 1


def test_nom_de_tache_dangereux_refuse(tmp_path):
    r = lancer(tmp_path, taches=[config("x'; Remove-Item *; '")])
    assert any("nom de tâche refusé" in e for e in r["erreurs"])


def test_config_taches_entrees_invalides_ecartees(tmp_path):
    taches = [config("bon"), config("bon"), {**config("zero"), "periode_min": 0}, {**config("f"), "fenetre": [5, 5]}]
    r = lancer(tmp_path, ps=faux_ps(tache("bon"), tache("f")), taches=taches)
    erreurs = " | ".join(r["erreurs"])
    assert "en double" in erreurs and "periode_min" in erreurs and "fenêtre invalide" in erreurs


@pytest.mark.parametrize("contenu", ["pas du json", '{"taches": 3}', "[]"])
def test_config_taches_illisible_dans_erreurs(tmp_path, contenu):
    r = lancer(tmp_path, brut={"veille-taches.json": contenu})
    assert r["erreurs"] and not r["alertes"]


@pytest.mark.parametrize("code,sortie", [(1, "[]"), (0, "pas du json"), (0, '[{"x": 1}]')])
def test_powershell_en_panne_les_autres_regles_continuent(tmp_path, code, sortie):
    def ps(_script):
        return code, sortie

    echeance = {"date": "2026-11-20", "libelle": "Rendu"}
    r = lancer(tmp_path, ps=ps, taches=[config()], echeances=[echeance])
    assert any("tâches Windows non lues" in e for e in r["erreurs"]) and "echeance:2026-11-20:rendu" in cles(r)


@pytest.mark.parametrize("exc", [FileNotFoundError("powershell"), OSError("x"), subprocess.TimeoutExpired("ps", 30)])
def test_powershell_absent_delai_ou_os(tmp_path, exc):
    def ps(_script):
        raise exc

    assert lancer(tmp_path, ps=ps, taches=[config()])["erreurs"]


def test_sortie_powershell_un_seul_objet_et_bom(tmp_path):
    def ps(_script):
        return 0, "\ufeff" + json.dumps(tache("T"))

    assert cles(lancer(tmp_path, ps=ps, taches=[config()])) == []


def test_pas_windows_la_source_est_ignoree_avec_un_message(tmp_path):
    ps = faux_ps()
    r = lancer(tmp_path, ps=ps, taches=[config()], windows=False)
    assert ps.scripts == [] and r["taches"] == [] and r["alertes"] == []
    assert any("non vérifié sur ce système" in n for n in r["notes"])


def test_scripts_powershell_en_lecture_seule():
    for script in (veille.script_powershell(["T"]), veille.script_refus_session(["T"])):
        assert '"' not in script  # une seule ligne, pas de guillemets doubles
        for verbe in ("Set-", "Remove-", "Stop-", "Disable-", "Enable-", "Register-", "Unregister-", "New-", "Start-"):
            assert verbe not in script
        assert "Get-" in script


def test_appel_powershell_reel_est_sans_profil_et_sans_stdin(monkeypatch):
    appels = []

    def faux_run(cmd, **kw):
        appels.append((cmd, kw))
        return subprocess.CompletedProcess(cmd, 0, stdout="[]", stderr="")

    monkeypatch.setattr(subprocess, "run", faux_run)
    monkeypatch.setattr("shutil.which", lambda nom: "C:/ps.exe")
    assert EXECUTEUR_POWERSHELL_REEL("Get-Date") == (0, "[]")
    cmd, kw = appels[0]
    assert (
        "-NoProfile" in cmd and "-NonInteractive" in cmd and kw["stdin"] == subprocess.DEVNULL and kw["timeout"] == 30
    )


def test_powershell_absent_du_systeme(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda nom: None)
    with pytest.raises(FileNotFoundError):
        EXECUTEUR_POWERSHELL_REEL("x")


# ---------- passages refusés (session Windows fermée) ----------
def test_silencieuse_avec_refus_de_session_devient_info(tmp_path):
    vieux = tache("T", dernier=MAINT - timedelta(hours=3))
    refus = [{"Nom": "T", "Quand": sec(MAINT - timedelta(hours=1))}]
    scripts = []

    def ps(script):
        scripts.append(script)
        return 0, json.dumps(refus if "Get-WinEvent" in script else [vieux])

    r = lancer(tmp_path, ps=ps, taches=[config()])
    a = alerte(r, "tache:T:silencieuse")
    assert a["niveau"] == "info" and "session Windows fermée" in a["detail"]
    assert sum("Get-WinEvent" in s for s in scripts) == 1


def test_refus_avant_le_dernier_passage_ne_compte_pas(tmp_path):
    vieux = tache("T", dernier=MAINT - timedelta(hours=3))
    refus = [{"Nom": "T", "Quand": sec(MAINT - timedelta(hours=5))}]

    def ps(script):
        return 0, json.dumps(refus if "Get-WinEvent" in script else [vieux])

    assert alerte(lancer(tmp_path, ps=ps, taches=[config()]), "tache:T:silencieuse")["niveau"] == "attention"


def test_aucune_lecture_d_evenements_sans_silencieuse(tmp_path):
    ps = faux_ps(tache("T"))
    lancer(tmp_path, ps=ps, taches=[config()])
    assert not any("Get-WinEvent" in s for s in ps.scripts)


def test_lire_passages_refuses_ignore_le_bruit_et_les_pannes():
    donnees = [
        {"Nom": "t", "Quand": sec(MAINT)},
        {"Nom": "Z", "Quand": sec(MAINT)},
        {"x": 1},
        5,
        {"Nom": "T", "Quand": 1},
    ]
    refus = veille.lire_passages_refuses(["T"], lambda s: (0, json.dumps(donnees)))
    assert refus == {"t": MAINT}  # « Z » n'est pas demandé, 1970 est « jamais », le bruit est ignoré
    assert veille.lire_passages_refuses(["T"], lambda s: (1, "[]")) == {}
    assert veille.lire_passages_refuses([], lambda s: (_ for _ in ()).throw(AppelReel())) == {}


# ---------- échéances ----------
@pytest.mark.parametrize(
    "jours,niveau",
    [(-1, "critique"), (0, "attention"), (7, "attention"), (8, "info"), (14, "info"), (15, None)],
)
def test_echeance_bornes(tmp_path, jours, niveau):
    jour = (MAINT.astimezone(FUSEAU).date() + timedelta(days=jours)).isoformat()
    r = lancer(tmp_path, echeances=[{"date": jour, "libelle": "Rendu"}])
    if niveau is None:
        assert r["alertes"] == []
    else:
        assert r["alertes"][0]["niveau"] == niveau


def test_echeance_sans_date_ignoree_et_champs_repris(tmp_path):
    r = lancer(
        tmp_path,
        echeances=[
            {"date": None, "libelle": "Plus tard"},
            {"date": "2026-11-20", "libelle": "Rendu", "projet": "demo", "carte": "Ma carte"},
        ],
    )
    a = r["alertes"][0]
    assert len(r["alertes"]) == 1 and a["projet"] == "demo" and a["carte_existante"] == "Ma carte"


def test_echeance_date_illisible_et_fichier_invalide(tmp_path):
    r = lancer(tmp_path / "a", echeances=[{"date": "31/12/2026", "libelle": "Mauvais format"}])
    assert any("date illisible" in e for e in r["erreurs"]) and not r["alertes"]
    for i, brut in enumerate(["pas du json", '{"a": 1}']):
        r = lancer(tmp_path / f"b{i}", brut={"echeances.json": brut})
        assert r["erreurs"]


def test_echeance_jour_local_et_non_utc(tmp_path):
    tard = datetime(2026, 11, 25, 23, 30, tzinfo=UTC)  # 01 h 30 le 26 en heure locale
    r = lancer(tmp_path, maintenant=tard, echeances=[{"date": "2026-11-25", "libelle": "Hier local"}])
    assert r["alertes"][0]["niveau"] == "critique"


# ---------- journal des missions ----------
def ligne(evenement, mission="m-20261125-01-ab12", minutes_avant=0, **extra):
    ts = (MAINT - timedelta(minutes=minutes_avant)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"ts": ts, "evenement": evenement, "mission": mission, **extra}


def test_mission_sans_fin_bornes(tmp_path):
    assert lancer(tmp_path / "a", journal=[ligne("lancee", minutes_avant=90)])["alertes"] == []
    r = lancer(tmp_path / "b", journal=[ligne("lancee", minutes_avant=91, projet="demo")])
    assert alerte(r, "journal:m-20261125-01-ab12")["niveau"] == "attention"


@pytest.mark.parametrize("fin", ["terminee", "echouee", "arretee", "permission_manquante"])
def test_mission_terminee_pas_d_alerte(tmp_path, fin):
    assert (
        lancer(tmp_path, journal=[ligne("lancee", minutes_avant=200), ligne(fin, minutes_avant=100)])["alertes"] == []
    )


def test_mission_relancee_apres_une_fin_est_signalee(tmp_path):
    r = lancer(
        tmp_path,
        journal=[
            ligne("lancee", minutes_avant=500),
            ligne("terminee", minutes_avant=400),
            ligne("lancee", minutes_avant=200),
        ],
    )
    assert len(r["alertes"]) == 1


def test_une_autre_mission_ne_ferme_pas_celle_ci(tmp_path):
    journal = [
        ligne("lancee", minutes_avant=200),
        ligne("terminee", mission="m-autre", minutes_avant=100),
        {"evenement": "lancee"},
    ]
    assert len(lancer(tmp_path, journal=journal)["alertes"]) == 1


def test_mission_mode_3_rien_avant_72_h_puis_info(tmp_path):
    assert lancer(tmp_path / "a", journal=[ligne("lancee", minutes_avant=72 * 60, mode=3)])["alertes"] == []
    r = lancer(tmp_path / "b", journal=[ligne("lancee", minutes_avant=72 * 60 + 1, mode=3)])
    assert r["alertes"][0]["niveau"] == "info"
    assert (
        lancer(tmp_path / "c", journal=[ligne("lancee", minutes_avant=200, mode=3), ligne("terminee")])["alertes"] == []
    )


def test_journal_corrompu_ou_absent(tmp_path):
    r = lancer(tmp_path / "a", brut={"missions.jsonl": "pas du json\n[1]\n"})
    assert r["alertes"] == [] and r["erreurs"] == []
    (tmp_path / "b").mkdir()
    r = veille.analyser(tmp_path / "b", MAINT, faux_ps(), faux_gh([]), FUSEAU, windows=True)
    assert any("missions.jsonl absent" in n for n in r["notes"]) and r["erreurs"] == []


# ---------- cartes ----------
def test_cartes_en_cours_bornes(tmp_path):
    trois = [carte("A"), carte("B"), carte("C")]
    assert lancer(tmp_path / "a", gh=faux_gh(trois))["alertes"] == []
    r = lancer(tmp_path / "b", gh=faux_gh([*trois, carte("D")]))
    assert alerte(r, "cartes:en_cours")["niveau"] == "info"


def test_cartes_poc_et_autres_colonnes_ne_comptent_pas(tmp_path):
    cartes = [carte("A"), carte("B"), carte("C"), carte("P", nature="POC"), carte("D", statut="Prêt")]
    assert lancer(tmp_path, gh=faux_gh(cartes))["alertes"] == []


@pytest.mark.parametrize(
    "executeur",
    [
        lambda a: kanban.Resultat(1, "", ""),
        lambda a: kanban.Resultat(0, "pas du json"),
        lambda a: (_ for _ in ()).throw(FileNotFoundError("gh")),
        lambda a: (_ for _ in ()).throw(subprocess.TimeoutExpired("gh", 30)),
        lambda a: (_ for _ in ()).throw(ValueError("inattendu")),
    ],
)
def test_gh_indisponible_seule_cette_regle_est_ignoree(tmp_path, executeur):
    r = lancer(tmp_path, gh=executeur, echeances=[{"date": "2026-11-20", "libelle": "Rendu"}])
    assert alerte(r, "cartes:illisibles")["niveau"] == "info" and "echeance:2026-11-20:rendu" in cles(r)


def test_kanban_non_configure_est_une_note(tmp_path):
    r = lancer(tmp_path, kanban_cfg=None)
    assert any("Kanban non configuré" in n for n in r["notes"]) and r["alertes"] == []


def test_carte_fait_n_est_pas_citee(tmp_path):
    echeance = {"date": "2026-11-20", "libelle": "Rendu", "carte": "Ma carte"}
    r = lancer(tmp_path / "a", echeances=[echeance], gh=faux_gh([carte("Ma carte", statut="Fait")]))
    assert alerte(r, "echeance:2026-11-20:rendu")["carte_existante"] is None
    r = lancer(tmp_path / "b", echeances=[echeance], gh=faux_gh([carte("Ma carte", statut="Prêt")]))
    assert alerte(r, "echeance:2026-11-20:rendu")["carte_existante"] == "Ma carte"


def test_retirer_cartes_faites_titre_insensible_aux_espaces_et_a_la_casse():
    a = veille._alerte("c", "info", "echeance", "t", "d", carte="  Ma   CARTE ")
    assert veille.retirer_cartes_faites([a], [carte(" ma carte", statut="Fait")])[0]["carte_existante"] is None
    assert veille.retirer_cartes_faites([a], [carte("ma carte", statut="Fait"), carte("ma carte", statut="Prêt")])[0][
        "carte_existante"
    ]


# ---------- tri, sortie ----------
def test_tri_niveau_puis_anciennete_puis_cle():
    def a(cle, niveau, depuis):
        return veille._alerte(cle, niveau, "tache", "t", "d", depuis=depuis)

    triees = veille.trier(
        [
            a("z", "info", None),
            a("b", "attention", "2026-01-02T00:00:00Z"),
            a("a", "attention", "2026-01-01T00:00:00Z"),
            a("c", "critique", None),
            a("d", "attention", None),
        ]
    )
    assert [x["cle"] for x in triees] == ["c", "a", "b", "d", "z"]


def test_resume_lisible(tmp_path):
    r = lancer(tmp_path, echeances=[{"date": "2026-11-20", "libelle": "Rendu", "carte": "Ma carte"}], kanban_cfg=None)
    lignes = veille.resume(r)
    assert lignes[0] == "Veille : 1 critique, 0 attention, 0 info."
    assert "(carte existante : Ma carte)" in lignes[1] and any(x.startswith("~ ") for x in lignes)


def test_main_ecrit_seulement_veille_json(tmp_path, capsys):
    d = dossier(tmp_path)
    code = veille.main(
        ["--donnees", str(d)],
        maintenant=lambda: MAINT,
        executer_ps=faux_ps(),
        executer_gh=faux_gh([]),
        fuseau=FUSEAU,
        racine=tmp_path,
        windows=True,
    )
    assert code == 0 and "Veille : 0 critique" in capsys.readouterr().out
    assert (d / "veille.json").is_file()
    assert json.loads((d / "veille.json").read_text(encoding="utf-8"))["genere_le"] == "2026-11-25T12:00:00Z"
    assert sorted(p.name for p in d.iterdir()) == sorted(
        ["veille-taches.json", "echeances.json", "missions.jsonl", "veille.json"]
    )


def test_main_sans_ecrire_et_json(tmp_path, capsys):
    d = dossier(tmp_path)
    veille.main(
        ["--donnees", str(d), "--sans-ecrire", "--json"], maintenant=lambda: MAINT, racine=tmp_path, windows=False
    )
    sortie = json.loads(capsys.readouterr().out)
    assert set(sortie) == {"genere_le", "alertes", "taches", "erreurs", "notes"}
    assert not (d / "veille.json").exists()


def test_ecriture_atomique_echec_garde_l_ancien_fichier(tmp_path, monkeypatch):
    cible = tmp_path / "veille.json"
    cible.write_text('{"ancien": true}', encoding="utf-8")

    def casse(*_a, **_k):
        raise OSError("disque plein")

    monkeypatch.setattr("os.replace", casse)
    with pytest.raises(OSError):
        commun.ecrire_json_atomique(cible, {"nouveau": True})
    assert json.loads(cible.read_text(encoding="utf-8")) == {"ancien": True}
    assert [p.name for p in tmp_path.iterdir()] == ["veille.json"]  # pas de fichier temporaire oublié


def test_main_echec_d_ecriture_code_1(tmp_path, monkeypatch, capsys):
    def casse(*_a, **_k):
        raise OSError("lecture seule")

    monkeypatch.setattr(commun, "ecrire_json_atomique", casse)
    d = dossier(tmp_path)
    assert veille.main(["--donnees", str(d)], maintenant=lambda: MAINT, racine=tmp_path, windows=False) == 1
    assert "impossible d'écrire" in capsys.readouterr().err


def test_exemples_du_depot_donnent_un_resume_sans_erreur(tmp_path, capsys):
    """Les deux fichiers d'exemple versionnés sont valides et lisibles (PowerShell simulé : aucune tâche trouvée).

    `racine=tmp_path` : sans config.json, la veille ne lit pas Orion."""
    code = veille.main(
        ["--exemples", "--sans-ecrire", "--donnees", str(RACINE_DEPOT / "donnees")],
        maintenant=lambda: datetime(2026, 11, 25, 12, 0, tzinfo=UTC),
        executer_ps=faux_ps(),
        fuseau=FUSEAU,
        racine=tmp_path,
        windows=True,
    )
    sortie = capsys.readouterr().out
    assert code == 0 and "Veille : 1 critique, 2 attention, 1 info." in sortie and "! " not in sortie


def test_aucun_secret_dans_la_sortie(tmp_path):
    d = dossier(tmp_path, echeances=[{"date": "2026-11-20", "libelle": "Rendu"}])
    r = veille.analyser(d, MAINT, faux_ps(), faux_gh([carte("A")]), FUSEAU, config_kanban=KANBAN, windows=True)
    texte = json.dumps(r).lower()
    for motif in ("token", "password", "secret", "authorization"):
        assert motif not in texte
