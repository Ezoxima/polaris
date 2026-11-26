"""Tests de `capacites` : exécutables, `which` et horloge SIMULÉS ; aucun appel réel à `claude`, `copilot`, `gh`, `git`.

Garde-fou : `subprocess.run` et `subprocess.Popen` lèvent `AppelReel` (une BaseException, pour qu'un `except Exception`
du code testé ne l'avale pas).
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime

import pytest

import capacites as cap

MAINT = datetime(2026, 11, 26, 10, 0, tzinfo=UTC)
AIDE_AVEC = """Usage: copilot [options]
  --model <model>      modèle (use 'auto' to let Copilot pick automatically)
  --no-auto-update     ne met pas le CLI à jour
  --usage-output-file <path>  écrit l'usage
"""
AIDE_SANS = "Usage: copilot [options]\n  --model <model>   modèle\n"


class AppelReel(BaseException):
    pass


@pytest.fixture(autouse=True)
def aucun_appel_reel(monkeypatch):
    def interdit(*_a, **_k):
        raise AppelReel("appel réel pendant un test")

    monkeypatch.setattr(subprocess, "run", interdit)
    monkeypatch.setattr(subprocess, "Popen", interdit)


class FauxLanceur:
    """Réponses par commande (sans le chemin) ; une exception est levée telle quelle ; note les appels."""

    def __init__(self, reponses=None, defaut=(0, "outil 1.2.3\n", "")):
        self.reponses = reponses or {}
        self.defaut = defaut
        self.appels = []

    def __call__(self, commande):
        self.appels.append(commande)
        r = self.reponses.get(tuple(commande[1:]), self.defaut)
        if isinstance(r, BaseException):
            raise r
        return r


def tout_present(nom):
    return f"/usr/bin/{nom}"


def par_nom(liste):
    return {c.nom: c for c in liste}


def inv(trouver=tout_present, lanceur=None, version=(3, 13, 1)):
    return par_nom(cap.inventaire(trouver, lanceur or FauxLanceur(), MAINT, version))


# ---------- détection ----------
def test_executables_presents_sont_disponibles_avec_leur_version():
    i = inv()
    for nom in ("cli_claude", "gh", "git"):
        assert i[nom].etat == cap.DISPONIBLE and "version : outil 1.2.3" in i[nom].note
        assert i[nom].date == "2026-11-26" and i[nom].source == cap.SOURCE_DETECTION


def test_executable_absent_est_indisponible():
    i = inv(trouver=lambda nom: None if nom == "gh" else tout_present(nom))
    assert i["gh"].etat == cap.INDISPONIBLE and "absent du PATH" in i["gh"].note
    assert i["git"].etat == cap.DISPONIBLE


@pytest.mark.parametrize(
    ("reponse", "cause"),
    [
        ((2, "", "boum"), "code de sortie 2 : boum"),
        ((0, "", ""), "sortie vide"),
        (subprocess.TimeoutExpired("x", 15), "TimeoutExpired"),
        (OSError("accès refusé"), "OSError (accès refusé)"),
    ],
)
def test_une_detection_qui_echoue_est_non_teste_avec_la_cause_jamais_disponible(reponse, cause):
    lanceur = FauxLanceur({("--version",): reponse})
    c = inv(lanceur=lanceur)["cli_claude"]
    assert c.etat == cap.NON_TESTE and cause in c.note and "n'a pas pu être lu" in c.note


def test_seule_la_version_et_l_aide_sont_lancees_jamais_un_service():
    lanceur = FauxLanceur({("--help",): (0, AIDE_AVEC, "")})
    inv(lanceur=lanceur)
    arguments = {tuple(c[1:]) for c in lanceur.appels}
    assert arguments <= {("--version",), ("--help",), ("--version", "--no-auto-update")}
    assert not any("auth" in " ".join(c) for c in lanceur.appels)


def test_gh_auth_est_toujours_non_teste_et_les_declaratives_aussi():
    i = inv()
    assert i["gh_auth"].etat == cap.NON_TESTE and "contacte le service" in i["gh_auth"].note
    for nom in ("sous_session", "taches_planifiees"):
        assert i[nom].etat == cap.NON_TESTE and "déclarative" in i[nom].note


def test_python_trop_ancien_est_indisponible():
    assert inv(version=(3, 13, 1))["python"].etat == cap.DISPONIBLE
    ancien = inv(version=(3, 9, 7))["python"]
    assert ancien.etat == cap.INDISPONIBLE and "3.9.7" in ancien.note and "3.11" in ancien.note


def test_toutes_les_capacites_sont_inventoriees_dans_l_ordre():
    assert [c.nom for c in cap.inventaire(tout_present, FauxLanceur(), MAINT, (3, 12, 0))] == list(cap.CAPACITES)


# ---------- copilot ----------
def test_copilot_version_lue_avec_no_auto_update_quand_l_aide_le_liste():
    lanceur = FauxLanceur(
        {("--help",): (0, AIDE_AVEC, ""), ("--version", "--no-auto-update"): (0, "copilot 9.9\n", "")}
    )
    c = inv(lanceur=lanceur)["cli_copilot"]
    assert c.etat == cap.DISPONIBLE
    assert "version : copilot 9.9 (lue avec --no-auto-update)" in c.note
    assert "--model auto documenté" in c.note
    assert ["/usr/bin/copilot", "--version", "--no-auto-update"] in lanceur.appels


def test_copilot_sans_no_auto_update_dans_l_aide_la_version_est_lue_sans():
    lanceur = FauxLanceur({("--help",): (0, AIDE_SANS, ""), ("--version",): (0, "copilot 1.0\n", "")})
    c = inv(lanceur=lanceur)["cli_copilot"]
    assert "(lue avec" not in c.note and "--model auto non documenté" in c.note
    assert ["/usr/bin/copilot", "--version"] in lanceur.appels


def test_copilot_aide_illisible_n_empeche_pas_la_version_mais_le_dit():
    lanceur = FauxLanceur({("--help",): (1, "", "erreur"), ("--version",): (0, "copilot 1.0\n", "")})
    c = inv(lanceur=lanceur)["cli_copilot"]
    assert c.etat == cap.DISPONIBLE and "aide non lue" in c.note and "code de sortie 1" in c.note


def test_copilot_script_ps1_est_signale_non_teste_sans_etre_lance():
    lanceur = FauxLanceur()
    c = inv(trouver=lambda nom: r"C:\outils\copilot.ps1" if nom == "copilot" else tout_present(nom), lanceur=lanceur)[
        "cli_copilot"
    ]
    assert c.etat == cap.NON_TESTE and ".ps1" in c.note and "SetShouldExit" in c.note
    assert not any(cmd[0].endswith("copilot.ps1") for cmd in lanceur.appels)


@pytest.mark.parametrize("chemin", [r"C:\outils\copilot.exe", r"C:\outils\copilot.cmd", "/usr/bin/copilot"])
def test_copilot_exe_cmd_ou_binaire_sont_lus_normalement(chemin):
    c = inv(trouver=lambda nom: chemin if nom == "copilot" else tout_present(nom))["cli_copilot"]
    assert c.etat == cap.DISPONIBLE


# ---------- déclarations et fusion ----------
def test_declaration_valide_et_invalide():
    c = cap.declaration("sous_session=disponible:testée à la main", "2026-11-26")
    assert (c.nom, c.etat, c.note, c.source) == ("sous_session", "disponible", "testée à la main", cap.SOURCE_DECLAREE)
    assert cap.declaration("taches_planifiees=indisponible", "d").note == "déclaré à la main"
    for mauvais in ("inconnue=disponible", "gh=peut-etre", "gh", "="):
        with pytest.raises(ValueError):
            cap.declaration(mauvais, "d")


def test_fusion_ne_ecrase_jamais_une_declaration_par_une_detection():
    existant = {
        "sous_session": {"etat": "disponible", "source": "declaree", "date": "2026-01-01", "note": "main"},
        "gh": {"etat": "indisponible", "source": "detection", "date": "2026-01-01", "note": "vieux"},
        "perso": {"etat": "disponible"},
    }
    detectees = [
        cap.Capacite("sous_session", cap.NON_TESTE, "déclarative", "2026-11-26"),
        cap.Capacite("gh", cap.DISPONIBLE, "version : 2", "2026-11-26"),
    ]
    section, rapport = cap.fusionner(existant, detectees)
    assert section["sous_session"]["etat"] == "disponible" and section["sous_session"]["note"] == "main"
    assert section["gh"]["etat"] == "disponible" and section["perso"] == {"etat": "disponible"}
    assert len(rapport) == 1 and "sous_session" in rapport[0]


def test_une_nouvelle_declaration_remplace_l_ancienne():
    existant = {"gh": {"etat": "disponible", "source": "declaree"}}
    section, rapport = cap.fusionner(existant, [cap.declaration("gh=indisponible", "d")])
    assert section["gh"]["etat"] == "indisponible" and rapport == []


@pytest.mark.parametrize("existant", [None, [], "x", 3])
def test_fusion_tolere_une_section_absente_ou_mal_formee(existant):
    section, _ = cap.fusionner(existant, [cap.Capacite("git", cap.DISPONIBLE)])
    assert list(section) == ["git"]


# ---------- programme ----------
def ecrire_config(tmp_path, **extra):
    config = {
        "_commentaire": "garde-moi",
        "moteur_par_defaut": "claude",
        "racine_projets": "~/x",
        "projets": {"demo": {"cwd": "demo", "autorise": ["a"]}},
        "kanban": {"numero": 3},
        **extra,
    }
    (tmp_path / "config.json").write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return config


def aller(tmp_path, *argv, trouver=tout_present, lanceur=None):
    return cap.main(
        list(argv), racine=tmp_path, trouver=trouver, lanceur=lanceur or FauxLanceur(), maintenant=lambda: MAINT
    )


def test_dry_run_par_defaut_n_ecrit_rien(tmp_path, capsys):
    ecrire_config(tmp_path)
    avant = (tmp_path / "config.json").read_bytes()
    assert aller(tmp_path) == 0
    sortie = capsys.readouterr().out
    assert "dry-run" in sortie and "cli_claude" in sortie and "disponible" in sortie
    assert (tmp_path / "config.json").read_bytes() == avant


def test_ecrire_ne_touche_que_la_section_capacites(tmp_path, capsys):
    avant = ecrire_config(tmp_path)
    assert aller(tmp_path, "--ecrire") == 0
    apres = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert {k: v for k, v in apres.items() if k != "capacites"} == avant
    assert list(apres["capacites"]) == list(cap.CAPACITES)
    assert apres["capacites"]["gh_auth"]["etat"] == "non_teste"
    assert not list(tmp_path.glob("*.tmp"))


def test_ecrire_conserve_une_declaration_a_la_main(tmp_path, capsys):
    ecrire_config(tmp_path, capacites={"sous_session": {"etat": "disponible", "source": "declaree", "note": "ok"}})
    assert aller(tmp_path, "--ecrire") == 0
    apres = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert apres["capacites"]["sous_session"]["etat"] == "disponible"
    assert "déclaration conservée" in capsys.readouterr().out


def test_declarer_avec_ecrire_enregistre_la_declaration(tmp_path):
    ecrire_config(tmp_path)
    assert aller(tmp_path, "--declarer", "sous_session=disponible:essayée", "--ecrire") == 0
    apres = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    s = apres["capacites"]["sous_session"]
    assert s["etat"] == "disponible" and s["source"] == "declaree" and s["note"] == "essayée"
    assert aller(tmp_path, "--ecrire") == 0  # une seconde détection ne l'écrase pas
    assert json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))["capacites"]["sous_session"] == s


def test_declarer_invalide_est_refuse_sans_ecrire(tmp_path, capsys):
    ecrire_config(tmp_path)
    assert aller(tmp_path, "--declarer", "n'importe=quoi", "--ecrire") == 2
    assert "REFUS" in capsys.readouterr().err
    assert "capacites" not in json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))


def test_ecrire_sans_config_refuse_et_ne_la_cree_pas(tmp_path, capsys):
    assert aller(tmp_path, "--ecrire") == 2
    assert "config.exemple.json" in capsys.readouterr().err and not (tmp_path / "config.json").exists()


def test_affichage_sans_config_est_possible(tmp_path, capsys):
    assert aller(tmp_path) == 0
    assert "affichage seul" in capsys.readouterr().err


def test_ecrire_refuse_une_section_capacites_mal_formee(tmp_path, capsys):
    ecrire_config(tmp_path, capacites=[1])
    avant = (tmp_path / "config.json").read_bytes()
    assert aller(tmp_path, "--ecrire") == 2
    assert "doit être un objet" in capsys.readouterr().err and (tmp_path / "config.json").read_bytes() == avant


# ---------- voies ----------
def etats(**kw):
    return {n: cap.Capacite(n, e) for n, e in kw.items()}


def test_voie_preferee_possible_est_proposee_sans_repli():
    c = cap.proposer_voie(etats(cli_claude="disponible"), "cli", "claude")
    assert (c.voie, c.repli) == ("cli", False)


def test_voie_cli_non_teste_ou_absente_se_replie_en_le_disant():
    for etat in ("non_teste", "indisponible"):
        c = cap.proposer_voie(etats(cli_claude=etat), "cli", "claude")
        assert c.voie == "prompt" and c.repli and "impossible" in c.raison and etat in c.raison


def test_repli_prefere_la_sous_session_declaree_au_prompt():
    c = cap.proposer_voie(etats(cli_copilot="indisponible", sous_session="disponible"), "cli", "copilot")
    assert c.voie == "sous_session" and c.repli


def test_moteur_choisit_le_bon_cli():
    capa = etats(cli_claude="indisponible", cli_copilot="disponible")
    assert cap.proposer_voie(capa, "cli", "copilot").voie == "cli"
    assert cap.proposer_voie(capa, "cli", "claude").voie == "prompt"


def test_sans_preference_valide_la_meilleure_voie_est_proposee():
    c = cap.proposer_voie(etats(cli_claude="disponible"), None, "claude")
    assert c.voie == "cli" and not c.repli
    c = cap.proposer_voie({}, "inconnue", "claude")
    assert c.voie == "prompt" and "aucune préférence valide" in c.raison


def test_le_prompt_est_toujours_possible():
    assert "prompt" in cap.voies_possibles({}, "claude")


def test_tableau_des_controles_couvre_chaque_voie_et_chaque_controle():
    texte = cap.tableau_controles()
    for libelle in cap.LIBELLES_CONTROLES.values():
        assert libelle in texte
    for voie in cap.VOIES:
        assert set(cap.GARANTIES[voie]) == set(cap.CONTROLES)
    assert cap.controles_non_garantis("cli") == ["relevé de consommation : " + cap.GARANTIES["cli"]["releve_conso"][1]]
    for voie in ("sous_session", "prompt"):
        assert len(cap.controles_non_garantis(voie)) == len(cap.CONTROLES)  # aucun contrôle équivalent au lanceur


def test_option_voie_du_programme_affiche_proposition_et_tableau(tmp_path, capsys):
    ecrire_config(tmp_path, voie_preferee="cli")
    lanceur = FauxLanceur()
    assert aller(tmp_path, "--voie", lanceur=lanceur, trouver=lambda n: None if n == "claude" else tout_present(n)) == 0
    sortie = capsys.readouterr().out
    assert "Voie proposée : prompt" in sortie and "REPLI" in sortie and "ne pas changer de voie" in sortie
    assert "verrou par projet" in sortie


def test_option_voie_utilise_les_declarations_deja_enregistrees(tmp_path, capsys):
    ecrire_config(
        tmp_path,
        voie_preferee="sous_session",
        capacites={"sous_session": {"etat": "disponible", "source": "declaree"}},
    )
    assert aller(tmp_path, "--voie") == 0
    assert "Voie proposée : sous_session" in capsys.readouterr().out


def test_lancer_local_n_est_jamais_appele_par_les_tests():
    with pytest.raises(AppelReel):
        cap.lancer_local(["copilot", "--version"])  # le garde-fou est actif : preuve qu'aucun test ne l'atteint
