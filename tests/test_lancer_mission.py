"""Tests de `lancer_mission` : `claude`, `copilot` et `gh` sont SIMULÉS, aucun appel réel.

Garde-fou : `subprocess.Popen`, `subprocess.run` et `kanban.executer_gh` lèvent `AppelReel` (une BaseException, pour
qu'un `except Exception` du code testé ne l'avale pas). Exécuteur, lecture d'Orion, git, horloge, attente, maintien
éveillé et recherche du moteur sont injectés ; tout vit dans des dossiers temporaires.
"""

from __future__ import annotations

import inspect
import json
import os
import subprocess
import threading
from datetime import UTC, datetime, timedelta

import pytest

import kanban
import lancer_mission as lm

MAINT = datetime(2026, 11, 25, 10, 0, tzinfo=UTC)
ID = "m-20261125-01-ab12"
ID2 = "m-20261125-02-cd34"


class AppelReel(BaseException):
    pass


@pytest.fixture(autouse=True)
def aucun_appel_reel(monkeypatch):
    def interdit(*_a, **_k):
        raise AppelReel("appel réel pendant un test")

    monkeypatch.setattr(subprocess, "Popen", interdit)
    monkeypatch.setattr(subprocess, "run", interdit)
    monkeypatch.setattr(kanban, "executer_gh", interdit)


# ---------- fabriques ----------
def brief(
    carte="Ajouter un export",
    colonne="Prêt",
    variante="FR",
    projet="demo",
    execution="modèle sonnet · effort high · mode 2 · durée max 60 min · conso estimée 4-8 % / 0-1 %",
):
    entete = f"Carte : {carte}" + (f" ({colonne})" if colonne else "") + f" — Variante : {variante} — Projet : {projet}"
    return f"{entete}\nObjectif : tester.\nExécution : {execution}\n"


def monde(tmp_path, texte=None, mission=ID, journal=(), projets=None, defauts=None, extra=None):
    """Arborescence temporaire : polaris (briefs, donnees, config.json) + des projets, dont `demo` avec un `.git`."""
    racine = tmp_path / "polaris"
    for d in ("briefs", "donnees"):
        (racine / d).mkdir(parents=True)
    base = tmp_path / "projets"
    (base / "demo" / "backend").mkdir(parents=True)
    (base / "demo" / ".git").mkdir()
    (base / "autre" / ".git").mkdir(parents=True)
    (base / "sansgit").mkdir()
    config = {
        "copilot": {"modeles": {"sonnet": "modele-standard", "opus": "modele-fort", "haiku": "modele-leger"}},
        "racine_projets": str(base),
        "defauts": defauts or {"budget_usd_par_minute": 0.2, "budget_usd_min": 3, "budget_usd_max": 20},
        "projets": projets
        or {
            "demo": {
                "cwd": "demo/backend",
                "git_root": "demo",
                "add_dirs": ["demo"],
                "autorise": ["Bash(python -m pytest*)"],
                "autorise_copilot": ["shell(python -m pytest)"],
            },
            "demo-bis": {"cwd": "demo", "git_root": "demo", "add_dirs": [], "autorise": []},
            "autre": {"cwd": "autre", "git_root": "autre", "add_dirs": [], "autorise": []},
            "sansgit": {"cwd": "sansgit", "git_root": None, "add_dirs": [], "autorise": []},
        },
        **(extra or {}),
    }
    (racine / "config.json").write_text(json.dumps(config), encoding="utf-8")
    if texte is not False:
        (racine / "briefs" / f"{mission}.md").write_text(texte if texte is not None else brief(), encoding="utf-8")
    ecrire_journal(racine, journal)
    return racine


def ecrire_journal(racine, evenements):
    (racine / "donnees" / "missions.jsonl").write_text(
        "".join(json.dumps(e) + "\n" for e in evenements), encoding="utf-8"
    )


def ev(evenement, mission=ID, minutes_avant=0, **extra):
    ts = (MAINT - timedelta(minutes=minutes_avant)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"ts": ts, "evenement": evenement, "mission": mission, **extra}


def sortie(
    result="Compte rendu de la mission.",
    is_error=False,
    subtype="success",
    cout=0.5,
    tours=7,
    session="sid-1",
    refus=(),
    duree=120.0,
    expire=False,
    err="",
):
    corps = {
        "type": "result",
        "subtype": subtype,
        "is_error": is_error,
        "result": result,
        "total_cost_usd": cout,
        "num_turns": tours,
        "session_id": session,
        "permission_denials": list(refus),
    }
    return lm.Sortie(json.dumps(corps), err, expire, duree, 0)


class FauxExecuteur:
    """Rejoue des résultats (le dernier se répète) ; note les appels et détecte tout chevauchement."""

    def __init__(self, *resultats, effet=None):
        self.resultats = list(resultats) or [sortie()]
        self.appels = []
        self.effet = effet
        self.actifs = 0
        self.chevauchement = False
        self.verrou = threading.Lock()

    def __call__(self, commande, cwd, entree, delai_s):
        with self.verrou:
            self.actifs += 1
            self.chevauchement = self.chevauchement or self.actifs > 1
            self.appels.append({"commande": commande, "cwd": cwd, "entree": entree, "delai_s": delai_s})
            numero = len(self.appels)
        try:
            if self.effet:
                self.effet(numero)
            r = self.resultats.pop(0) if len(self.resultats) > 1 else self.resultats[0]
            if isinstance(r, BaseException):
                raise r
            return r
        finally:
            with self.verrou:
                self.actifs -= 1


class FauxGit:
    def __init__(self, head="aaaa1111", distant="origine1", statut=(" M a.py",), log="bbbb2222 feat: x"):
        self.head, self.distant, self.statut, self.log = head, distant, list(statut), log

    def __call__(self, depot, *args):
        if args[:2] == ("rev-parse", "HEAD"):
            return self.head
        if args[:2] == ("rev-parse", "@{u}"):
            return self.distant
        if args[0] == "status":
            return "\n".join(self.statut)
        if args[0] == "log":
            return self.log
        raise AssertionError(f"commande git inattendue : {args}")


class Attentes(list):
    def __call__(self, secondes):
        self.append(secondes)


def aller(
    racine,
    *ids,
    executer=None,
    git=None,
    dormir=None,
    argv=(),
    trouver=None,
    aide="",
):
    executer = executer or FauxExecuteur()
    return lm.main(
        [*ids, *argv],
        racine=racine,
        executer=executer,
        maintenant=lambda: MAINT,
        dormir=dormir if dormir is not None else Attentes(),
        git=git or FauxGit(),
        eveil=lambda actif: None,
        trouver=trouver or (lambda nom: f"/usr/bin/{nom}"),
        aide_copilot=lambda: aide,
    )


def journal(racine):
    return [
        json.loads(ligne) for ligne in (racine / "donnees" / "missions.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def compte_rendu(racine, mission=ID):
    return (racine / "briefs" / f"{mission}-compte-rendu.md").read_text(encoding="utf-8")


# ---------- lecture du brief ----------
def test_lire_brief_nominal():
    b = lm.lire_brief(brief())
    assert b["carte"] == "Ajouter un export" and b["colonne"] == "Prêt"
    assert b["variante"] == "FR" and b["projet"] == "demo"
    assert (b["modele"], b["effort"], b["mode"], b["duree_max_min"]) == ("sonnet", "high", 2, 60)
    assert b["budget_usd"] is None


@pytest.mark.parametrize("valeur", ["—", "-", "", "–"])
def test_variante_absente(valeur):
    assert lm.lire_brief(brief(variante=valeur))["variante"] is None


def test_variante_libre_sans_liste_fermee():
    assert lm.lire_brief(brief(variante="client Dupont"))["variante"] == "client Dupont"


def test_duree_en_heures_et_budget():
    b = lm.lire_brief(brief(execution="modèle opus · effort medium · mode 2 · durée max 1,5 h · budget 6 USD"))
    assert b["duree_max_min"] == 90 and b["budget_usd"] == 6 and b["modele"] == "opus"


@pytest.mark.parametrize(
    "texte,fragment",
    [
        ("Pas d'en-tête\nExécution : modèle sonnet · effort high · mode 2 · durée max 10 min", "Carte :"),
        ("Carte : X — Variante : — — Projet : demo\nObjectif : y", "Exécution"),
        (brief(execution="effort high · mode 2 · durée max 10 min"), "modèle"),
        (brief(execution="modèle sonnet · mode 2 · durée max 10 min"), "effort"),
        (brief(execution="modèle sonnet · effort high · durée max 10 min"), "mode"),
        (brief(execution="modèle sonnet · effort high · mode 2"), "durée"),
        (brief(execution="modèle sonnet · effort énorme · mode 2 · durée max 10 min"), "effort"),
    ],
)
def test_brief_illisible(texte, fragment):
    with pytest.raises(lm.Refus, match=fragment):
        lm.lire_brief(texte)


# ---------- préparation et refus ----------
def preparer(racine, mission=ID, moteur="claude", aide=None):
    config = json.loads((racine / "config.json").read_text(encoding="utf-8"))
    return lm.preparer(mission, racine, config, moteur, aide)


def test_preparer_claude_construit_la_commande(tmp_path):
    racine = monde(tmp_path)
    p = preparer(racine)
    assert p.projet == "demo" and p.variante == "FR" and p.moteur == "claude"
    cmd = p.commande
    assert cmd[:2] == ["claude", "-p"]
    assert cmd[cmd.index("--model") + 1] == "sonnet" and cmd[cmd.index("--effort") + 1] == "high"
    assert "--add-dir" in cmd and "--max-budget-usd" in cmd
    autorises = cmd[cmd.index("--allowedTools") + 1 : cmd.index("--disallowedTools")]
    interdits = cmd[cmd.index("--disallowedTools") + 1 :]
    assert "Bash(python -m pytest*)" in autorises
    assert "Bash(git push*)" in interdits and "PowerShell(git push*)" in interdits
    assert not any("git push" in a for a in autorises)
    assert p.entree == p.prompt and "Règles communes (Polaris)" in p.prompt


def test_budget_calcule_borne(tmp_path):
    racine = monde(tmp_path, texte=brief(execution="modèle sonnet · effort high · mode 2 · durée max 100 min"))
    assert preparer(racine).budget_usd == 20  # 100 min × 0,2 = 20, borné à 20
    racine = monde(tmp_path / "b", texte=brief(execution="modèle sonnet · effort high · mode 2 · durée max 5 min"))
    assert preparer(racine).budget_usd == 3  # plancher


@pytest.mark.parametrize(
    "execution,fragment",
    [
        ("modèle sonnet · effort high · mode 3 · durée max 10 min", "mode 3"),
        ("modèle opus · effort xhigh · mode 2 · durée max 10 min", "ne dépasse jamais"),
        ("modèle opus · effort max · mode 2 · durée max 10 min", "ne dépasse jamais"),
        ("modèle sonnet · effort high · mode 2 · durée max 500 min", "durée max"),
        ("modèle sonnet · effort high · mode 2 · durée max 10 min · budget 999 USD", "budget"),
    ],
)
def test_refus_de_parametres(tmp_path, execution, fragment):
    racine = monde(tmp_path, texte=brief(execution=execution))
    with pytest.raises(lm.Refus, match=fragment):
        preparer(racine)


def test_opus_high_accepte(tmp_path):
    racine = monde(tmp_path, texte=brief(execution="modèle opus · effort high · mode 2 · durée max 30 min"))
    assert preparer(racine).modele == "opus"


def test_refus_projet_absent_brief_absent_id_invalide(tmp_path):
    racine = monde(tmp_path, texte=brief(projet="inconnu"))
    with pytest.raises(lm.Refus, match="absent de config.json"):
        preparer(racine)
    racine = monde(tmp_path / "x", texte=False)
    with pytest.raises(lm.Refus, match="introuvable"):
        preparer(racine)
    with pytest.raises(lm.Refus, match="identifiant"):
        lm.preparer("n-importe-quoi", racine, {"projets": {}})


def test_refus_dossier_introuvable(tmp_path):
    projets = {"demo": {"cwd": "n-existe-pas", "git_root": None}}
    racine = monde(tmp_path, projets=projets)
    with pytest.raises(lm.Refus, match="dossier de travail introuvable"):
        preparer(racine)


def test_moteur_inconnu(tmp_path):
    with pytest.raises(lm.Refus, match="moteur"):
        preparer(monde(tmp_path), moteur="gpt")


# ---------- moteur copilot ----------
def test_copilot_commande_et_notes(tmp_path):
    modeles = {"copilot": {"modeles": {"sonnet": "modele-standard"}}}
    racine = monde(tmp_path, extra=modeles)
    p = preparer(racine, moteur="copilot")
    cmd = p.commande
    assert cmd[:2] == ["copilot", "-p"] and cmd[2] == p.prompt
    assert "-s" in cmd and "--no-ask-user" in cmd
    assert "--model=modele-standard" in cmd
    assert "--allow-tool=shell(python -m pytest)" in cmd and "--allow-tool=write" in cmd
    assert "--deny-tool=shell(git push)" in cmd and "--deny-tool=shell(git reset)" in cmd
    assert not any(a.startswith("--allow-tool=") and "push" in a for a in cmd)
    assert p.entree == ""  # le prompt passe par l'argument, pas par l'entrée standard
    assert any("effort du brief non transmis" in n for n in p.notes) and any("non testés" in n for n in p.notes)
    assert p.options_detectees == [] and p.options_transmises == []


@pytest.mark.parametrize("extra", [{"copilot": {"modeles": {"sonnet": "  "}}}, {"copilot": {}}, {"copilot": 3}])
def test_copilot_sans_modele_declare_refuse_et_nomme_la_cle(tmp_path, extra):
    racine = monde(tmp_path, extra=extra)
    with pytest.raises(lm.Refus, match=r"copilot\.modeles\.sonnet"):
        preparer(racine, moteur="copilot")


def test_projet_absent_renvoie_a_l_etape_de_configuration(tmp_path):
    racine = monde(tmp_path, texte=brief(projet="inconnu"))
    with pytest.raises(lm.Refus, match="absent de config.json.*docs/installation.md"):
        preparer(racine, moteur="copilot")


# Textes d'aide FICTIFS (aucun appel à `copilot --help`) : ancienne version sans les options, version récente avec.
AIDE_ANCIENNE = """Usage: copilot [options]
  -p, --prompt <texte>   prompt non interactif
  --model <modele>       modèle
  --allow-tool <outil>   autorise un outil
"""
AIDE_RECENTE = """Usage: copilot [options]
  -p, --prompt <texte>        prompt non interactif
  --reasoning-effort <level>  effort de raisonnement (choices: "low", "medium", "high")
  --max-ai-credits <n>        plafond de crédits IA
  --usage-output-file <path>  écrit l'usage dans un fichier
  --allow-all-tools           autorise tous les outils (requis en mode non interactif)
"""
AIDE_SANS_LISTE = AIDE_RECENTE.replace(' (choices: "low", "medium", "high")', "")


def test_analyser_aide_ancienne_version():
    a = lm.analyser_aide_copilot(AIDE_ANCIENNE)
    assert a.lue and a.options == frozenset() and a.efforts == ()


def test_analyser_aide_recente_version():
    a = lm.analyser_aide_copilot(AIDE_RECENTE)
    assert a.options == frozenset(lm.OPTIONS_COPILOT_SUIVIES) - {"--no-auto-update"}
    assert not a.modele_auto
    assert a.efforts == ("low", "medium", "high")
    assert lm.analyser_aide_copilot(AIDE_SANS_LISTE).efforts == ()


@pytest.mark.parametrize("texte", [None, "", "  \n"])
def test_analyser_aide_absente(texte):
    assert lm.analyser_aide_copilot(texte) == lm.AideCopilot()


def test_analyser_aide_ne_confond_pas_les_prefixes():
    a = lm.analyser_aide_copilot("  --max-ai-credits-extra <n>\n  --usage-output-files x\n")
    assert a.options == frozenset()


# Aide FICTIVE d'une version qui documente `auto` pour --model et propose --no-auto-update.
AIDE_AUTO = (
    AIDE_RECENTE
    + """  --model <model>             modèle à utiliser (use 'auto' to let Copilot pick automatically)
  --no-auto-update            ne met pas le CLI à jour
"""
)


def test_analyser_aide_detecte_auto_seulement_dans_le_texte_de_model():
    assert lm.analyser_aide_copilot(AIDE_AUTO).modele_auto
    assert not lm.analyser_aide_copilot(AIDE_ANCIENNE).modele_auto
    # « auto » ailleurs (--no-auto-update, autre option) ne prouve rien
    autre = (
        "  --model <m>   modèle"
        + chr(10)
        + "  --no-auto-update   pas de mise à jour"
        + chr(10)
        + "  --x   mode auto"
        + chr(10)
    )
    assert not lm.analyser_aide_copilot(autre).modele_auto
    assert not lm.analyser_aide_copilot("  --model-x <m>   use 'auto'" + chr(10)).modele_auto
    assert "--no-auto-update" in lm.analyser_aide_copilot(AIDE_AUTO).options


def test_copilot_modele_auto_transmis_si_l_aide_le_documente(tmp_path):
    extra = {"copilot": {"modeles": {"sonnet": "auto"}}}
    p = preparer(monde(tmp_path, extra=extra), moteur="copilot", aide=AIDE_AUTO)
    assert "--model=auto" in p.commande
    assert any("« auto »" in n and "currentModel" in n for n in p.notes)


@pytest.mark.parametrize("aide", [AIDE_RECENTE, AIDE_ANCIENNE, ""])
def test_copilot_modele_auto_refuse_si_l_aide_ne_le_documente_pas(tmp_path, aide):
    extra = {"copilot": {"modeles": {"sonnet": " Auto "}}}
    with pytest.raises(lm.Refus, match=r"« auto ».*ne documente pas"):
        preparer(monde(tmp_path, extra=extra), moteur="copilot", aide=aide)


def test_copilot_modele_vide_reste_refuse_meme_si_auto_est_documente(tmp_path):
    extra = {"copilot": {"modeles": {"sonnet": ""}}}
    with pytest.raises(lm.Refus, match=r"copilot\.modeles\.sonnet"):
        preparer(monde(tmp_path, extra=extra), moteur="copilot", aide=AIDE_AUTO)


def test_copilot_no_auto_update_transmis_seulement_si_l_aide_le_liste(tmp_path):
    assert "--no-auto-update" in preparer(monde(tmp_path), moteur="copilot", aide=AIDE_AUTO).commande
    assert "--no-auto-update" not in preparer(monde(tmp_path / "2"), moteur="copilot", aide=AIDE_RECENTE).commande
    assert "--no-auto-update" not in preparer(monde(tmp_path / "3"), moteur="copilot", aide="").commande


def test_copilot_recent_transmet_effort_et_fichier_d_usage_sans_credits_par_defaut(tmp_path):
    p = preparer(monde(tmp_path), moteur="copilot", aide=AIDE_RECENTE)
    assert "--reasoning-effort=high" in p.commande
    assert not any(a.startswith("--max-ai-credits") for a in p.commande)  # jamais déduit du budget USD
    assert any(a.startswith("--usage-output-file=") for a in p.commande)
    assert "--allow-all-tools" not in p.commande
    assert p.options_transmises == ["--reasoning-effort", "--usage-output-file"]
    assert any("aucun plafond n'est fixé" in n and "pas des dollars" in n for n in p.notes)
    assert p.commande.count("--deny-tool=shell(git push)") == 1


def test_copilot_ancien_ne_transmet_rien_de_facultatif(tmp_path):
    p = preparer(monde(tmp_path), moteur="copilot", aide=AIDE_ANCIENNE)
    assert p.options_transmises == []
    assert not any(a.startswith(("--reasoning", "--max-ai", "--usage")) for a in p.commande)
    assert any("--reasoning-effort : absent de l'aide" in n for n in p.notes)


def test_copilot_effort_hors_liste_refuse(tmp_path):
    racine = monde(tmp_path, texte=brief(execution="modèle sonnet · effort xhigh · mode 2 · durée max 60 min"))
    with pytest.raises(lm.Refus, match="--reasoning-effort.*low, medium, high.*xhigh"):
        preparer(racine, moteur="copilot", aide=AIDE_RECENTE)


def test_copilot_effort_sans_liste_dans_l_aide(tmp_path):
    racine = monde(tmp_path, texte=brief(execution="modèle sonnet · effort max · mode 2 · durée max 60 min"))
    p = preparer(racine, moteur="copilot", aide=AIDE_SANS_LISTE)
    assert not any(a.startswith("--reasoning-effort") for a in p.commande)
    assert any("effort « max » non transmis" in n for n in p.notes)
    p2 = preparer(monde(tmp_path / "2"), moteur="copilot", aide=AIDE_SANS_LISTE)
    assert "--reasoning-effort=high" in p2.commande


def test_copilot_credits_ia_dans_la_config(tmp_path):
    extra = {"copilot": {"modeles": {"sonnet": "m"}, "credits_ia_max": 25}}
    p = preparer(monde(tmp_path, extra=extra), moteur="copilot", aide=AIDE_RECENTE)
    assert "--max-ai-credits=25" in p.commande
    assert not any("USD" in a for a in p.commande)
    p = preparer(monde(tmp_path / "2", extra=extra), moteur="copilot", aide=AIDE_ANCIENNE)
    assert not any(a.startswith("--max-ai-credits") for a in p.commande)
    assert any("`copilot.credits_ia_max` = 25 ignoré" in n for n in p.notes)


@pytest.mark.parametrize("valeur", [0, -3, 2.5, "10", True])
def test_copilot_credits_invalides_refuses(tmp_path, valeur):
    extra = {"copilot": {"modeles": {"sonnet": "m"}, "credits_ia_max": valeur}}
    with pytest.raises(lm.Refus, match="credits_ia_max"):
        preparer(monde(tmp_path, extra=extra), moteur="copilot", aide=AIDE_RECENTE)


def test_copilot_allow_all_tools_par_defaut_non_transmis(tmp_path):
    p = preparer(monde(tmp_path), moteur="copilot", aide=AIDE_RECENTE)
    assert "--allow-all-tools" not in p.commande and not p.tous_outils
    assert "--allow-tool=write" in p.commande


def test_copilot_allow_all_tools_sur_choix_garde_les_interdits(tmp_path):
    extra = {"copilot": {"modeles": {"sonnet": "m"}, "autoriser_tous_outils": True}}
    p = preparer(monde(tmp_path, extra=extra), moteur="copilot", aide=AIDE_RECENTE)
    assert "--allow-all-tools" in p.commande and p.tous_outils
    for interdit in lm.INTERDITS_COPILOT:
        assert f"--deny-tool={interdit}" in p.commande
    assert any(n.startswith("AVERTISSEMENT") and "--deny-tool" in n for n in p.notes)
    p = preparer(monde(tmp_path / "2", extra=extra), moteur="copilot", aide=AIDE_ANCIENNE)
    assert "--allow-all-tools" not in p.commande  # l'aide ne le liste pas : pas d'option inconnue


@pytest.mark.parametrize("valeur", ["oui", 1, None])
def test_copilot_autoriser_tous_outils_doit_etre_booleen(tmp_path, valeur):
    extra = {"copilot": {"modeles": {"sonnet": "m"}, "autoriser_tous_outils": valeur}}
    with pytest.raises(lm.Refus, match="autoriser_tous_outils"):
        preparer(monde(tmp_path, extra=extra), moteur="copilot")


def test_dry_run_copilot_affiche_options_detectees_et_transmises(tmp_path, capsys):
    racine = monde(tmp_path)
    assert aller(racine, ID, argv=["--dry-run", "--moteur", "copilot"], aide=AIDE_RECENTE) == 0
    sortie_ = capsys.readouterr().out
    assert "détectées : --allow-all-tools, --max-ai-credits, --reasoning-effort, --usage-output-file" in sortie_
    assert "transmises : --reasoning-effort, --usage-output-file" in sortie_
    assert not (racine / "donnees" / f"usage-{ID}.json").exists()


def test_motif_allow_all_tools_reconnu():
    assert lm.exige_allow_all_tools(lm.Sortie("", "Error: --allow-all-tools is required", False, 1, 1))
    assert lm.exige_allow_all_tools(lm.Sortie("please use allow all tools", "", False, 1, 1))
    assert not lm.exige_allow_all_tools(lm.Sortie("", "authentification requise", False, 1, 1))
    assert not lm.exige_allow_all_tools(lm.Sortie("--allow-all-tools", "", False, 1, 0))  # code 0 : pas une erreur


def test_mission_copilot_qui_reclame_allow_all_tools_s_arrete_sans_relance(tmp_path, capsys):
    racine = monde(tmp_path)
    ko = FauxExecuteur(lm.Sortie("", "error: --allow-all-tools required in non-interactive mode", False, 2.0, 1))
    assert aller(racine, ID, argv=["--moteur", "copilot"], executer=ko) == 1
    assert len(ko.appels) == 1 and "--allow-all-tools" not in ko.appels[0]["commande"]
    assert "ne l'ajoute PAS" in capsys.readouterr().err
    assert "docs/garde-fous.md" in compte_rendu(racine) and "autoriser_tous_outils" in compte_rendu(racine)
    assert "réclame --allow-all-tools" in journal(racine)[-1]["note"]


# Fichiers d'usage FICTIFS (format observé sur une version du CLI, non garanti).
USAGE_COMPLET = {
    "currentModel": "modele-x",
    "totalPremiumRequestCost": 1.5,
    "totalUserRequests": 2,
    "totalNanoAiu": 123456,
    "aiCreditsStatus": "ok",
    "tokenDetails": {
        "input": {"tokenCount": 1000},
        "cache_read": {"tokenCount": 400},
        "cache_write": {"tokenCount": 0},
        "output": {"tokenCount": 250},
    },
    "codeChanges": {"linesAdded": 12, "linesRemoved": 3, "filesModifiedCount": 2, "filesModified": ["a", "b"]},
    "modelMetrics": {"modele-x": {"n": 1}},
}


def ecrire_usage(tmp_path, contenu):
    f = tmp_path / "usage.json"
    f.write_text(contenu if isinstance(contenu, str) else json.dumps(contenu), encoding="utf-8")
    return f


def test_usage_complet_champs_connus_et_reste_brut(tmp_path):
    f = ecrire_usage(tmp_path, USAGE_COMPLET)
    u = lm.lire_usage(f)
    assert u.modele == "modele-x" and not f.exists()
    for attendu in (
        "non garanti",
        "modèle modele-x",
        "coût premium 1.5",
        "nanoAIU 123456",
        "jetons entrée 1000, cache lu 400, cache écrit 0, sortie 250",
        "code +12 -3 2 fichier(s)",
        "reste brut :",
        "aiCreditsStatus",
        "modelMetrics",
    ):
        assert attendu in u.resume, attendu
    assert "currentModel" not in u.resume.split("reste brut :")[1]  # les champs connus ne sont pas répétés


def test_usage_partiel_tolere_les_absences_sans_inventer_le_modele(tmp_path):
    u = lm.lire_usage(ecrire_usage(tmp_path, {"totalNanoAiu": 9}))
    assert u.modele is None
    assert "nanoAIU 9" in u.resume and "modèle non relevé" in u.resume and "coût premium" not in u.resume


def test_usage_sans_aucun_champ_connu_garde_le_brut_tronque(tmp_path):
    u = lm.lire_usage(ecrire_usage(tmp_path, {"x": 1, "y": "z" * 600}))
    assert "aucun champ connu relevé" in u.resume and "modèle non relevé" in u.resume
    assert u.resume.endswith("…") and len(u.resume) < 700


@pytest.mark.parametrize("contenu", ["pas du json {", "[1, 2]", '"texte"', "42"])
def test_usage_invalide_ou_inattendu_est_dit_avec_le_brut(tmp_path, contenu):
    u = lm.lire_usage(ecrire_usage(tmp_path, contenu))
    assert u.modele is None and "JSON invalide ou inattendu" in u.resume and contenu in u.resume


def test_usage_champ_de_type_inattendu_signale_et_ne_donne_pas_de_modele(tmp_path):
    f = ecrire_usage(tmp_path, {"currentModel": 5, "totalNanoAiu": "beaucoup", "codeChanges": [1], "tokenDetails": 3})
    u = lm.lire_usage(f)
    assert u.modele is None
    assert "type inattendu : currentModel, totalNanoAiu, tokenDetails, codeChanges" in u.resume
    assert lm.lire_usage(ecrire_usage(tmp_path, {"currentModel": "  "})).modele is None
    assert lm.lire_usage(ecrire_usage(tmp_path, {"totalNanoAiu": True})).resume.count("type inattendu") == 1


def test_usage_absent_vide_ou_illisible(tmp_path):
    assert lm.lire_usage(tmp_path / "absent.json") == lm.Usage(None, "fichier d'usage non produit")
    assert lm.lire_usage(ecrire_usage(tmp_path, "  " + chr(10))).resume == "fichier d'usage vide"
    assert "illisible" in lm.lire_usage(tmp_path).resume  # un dossier : erreur d'E/S, pas un fichier absent


def test_fichier_d_usage_resume_dans_le_journal_et_le_compte_rendu(tmp_path):
    racine = monde(tmp_path)
    cible = racine / "donnees" / f"usage-{ID}.json"

    def effet(_n):
        cible.write_text(json.dumps(USAGE_COMPLET), encoding="utf-8")

    faux = FauxExecuteur(lm.Sortie("Fait.", "", False, 5.0, 0), effet=effet)
    assert aller(racine, ID, argv=["--moteur", "copilot"], executer=faux, aide=AIDE_RECENTE) == 0
    fin = journal(racine)[-1]
    assert "usage (format observé sur une version, non garanti) : modèle modele-x" in fin["note"]
    assert fin["modele_reel"] == "modele-x" and fin["modele"] == "sonnet"  # classe demandée ≠ modèle réel
    cr = compte_rendu(racine)
    assert "Consommation Copilot" in cr and "Modèle réellement utilisé : modele-x" in cr
    assert not cible.exists()


def test_modele_reel_non_releve_sans_fichier_d_usage_ni_champ(tmp_path):
    racine = monde(tmp_path)
    faux = FauxExecuteur(lm.Sortie("Fait.", "", False, 5.0, 0))
    assert aller(racine, ID, argv=["--moteur", "copilot"], executer=faux, aide=AIDE_RECENTE) == 0
    assert journal(racine)[-1]["modele_reel"] == "non relevé"
    assert "Modèle réellement utilisé : non relevé" in compte_rendu(racine)
    racine2 = monde(tmp_path / "2")  # aide ancienne : pas de fichier d'usage demandé
    assert (
        aller(racine2, ID, argv=["--moteur", "copilot"], executer=FauxExecuteur(lm.Sortie("ok", "", False, 5, 0))) == 0
    )
    assert journal(racine2)[-1]["modele_reel"] == "non relevé"


def test_claude_n_ecrit_pas_de_modele_reel(tmp_path):
    racine = monde(tmp_path)
    assert aller(racine, ID) == 0
    assert "modele_reel" not in journal(racine)[-1]


def test_modele_auto_de_bout_en_bout_journalise_le_modele_reel(tmp_path):
    extra = {"copilot": {"modeles": {"sonnet": "auto"}}}
    racine = monde(tmp_path, extra=extra)
    cible = racine / "donnees" / f"usage-{ID}.json"
    faux = FauxExecuteur(
        lm.Sortie("Fait.", "", False, 5.0, 0), effet=lambda _n: cible.write_text('{"currentModel": "choisi"}', "utf-8")
    )
    assert aller(racine, ID, argv=["--moteur", "copilot"], executer=faux, aide=AIDE_AUTO + "") == 0
    assert "--model=auto" in faux.appels[0]["commande"]
    assert journal(racine)[-1]["modele_reel"] == "choisi"


def test_fichier_d_usage_absent_est_signale_sans_invention(tmp_path):
    racine = monde(tmp_path)
    faux = FauxExecuteur(lm.Sortie("Fait.\n", "", False, 5.0, 0))
    assert aller(racine, ID, argv=["--moteur", "copilot"], executer=faux, aide=AIDE_RECENTE) == 0
    assert "fichier d'usage non produit" in journal(racine)[-1]["note"]


def test_un_vieux_fichier_d_usage_n_est_pas_relu(tmp_path):
    racine = monde(tmp_path)
    (racine / "donnees" / f"usage-{ID}.json").write_text("ancien", encoding="utf-8")
    faux = FauxExecuteur(lm.Sortie("Fait.\n", "", False, 5.0, 0))
    assert aller(racine, ID, argv=["--moteur", "copilot"], executer=faux, aide=AIDE_RECENTE) == 0
    assert "ancien" not in journal(racine)[-1]["note"]


def test_claude_ne_lit_pas_l_aide_de_copilot(tmp_path):
    appels = []
    code = lm.main(
        [ID, "--dry-run"],
        racine=monde(tmp_path),
        maintenant=lambda: MAINT,
        trouver=lambda n: "/x",
        aide_copilot=lambda: appels.append(1) or "",
    )
    assert code == 0 and appels == []  # `copilot --help` n'est lu que pour le moteur copilot


def test_copilot_brief_trop_long_refuse(tmp_path):
    racine = monde(tmp_path, texte=brief() + "x" * 31000)
    with pytest.raises(lm.Refus, match="trop long"):
        preparer(racine, moteur="copilot")


def test_copilot_succes_et_echec(tmp_path):
    racine = monde(tmp_path)
    ok = FauxExecuteur(lm.Sortie("Fait : tout.\n", "", False, 30.0, 0))
    assert aller(racine, ID, argv=["--moteur", "copilot"], executer=ok) == 0
    assert "Fait : tout." in compte_rendu(racine)
    assert ok.appels[0]["commande"][0] == "copilot"
    assert journal(racine)[-1]["evenement"] == "terminee" and journal(racine)[-1]["moteur"] == "copilot"
    assert "coût non fourni" in journal(racine)[-1]["note"]

    racine2 = monde(tmp_path / "2")
    ko = FauxExecuteur(lm.Sortie("", "authentification requise", False, 3.0, 1))
    assert aller(racine2, ID, argv=["--moteur", "copilot"], executer=ko) == 1
    assert journal(racine2)[-1]["evenement"] == "echouee"


def test_moteur_par_defaut_de_la_config(tmp_path):
    racine = monde(tmp_path, extra={"moteur_par_defaut": "copilot"})
    faux = FauxExecuteur(lm.Sortie("ok", "", False, 1.0, 0))
    assert aller(racine, ID, executer=faux) == 0
    assert faux.appels[0]["commande"][0] == "copilot"


def test_moteur_introuvable_refuse(tmp_path, capsys):
    racine = monde(tmp_path)
    faux = FauxExecuteur()
    assert aller(racine, ID, executer=faux, trouver=lambda nom: None) == 2
    assert "introuvable dans le PATH" in capsys.readouterr().err
    assert faux.appels == []


# ---------- journal et exclusion par projet ----------
def test_mission_en_cours_bornes():
    lancee = [ev("lancee", minutes_avant=60)]
    assert lm.mission_en_cours(lancee, ID, MAINT) is not None
    assert lm.mission_en_cours(lancee + [ev("terminee")], ID, MAINT) is None
    assert lm.mission_en_cours([ev("lancee", minutes_avant=181)], ID, MAINT) is None  # le blocage tombe au bout de 3 h


def test_refus_mission_deja_en_cours(tmp_path, capsys):
    racine = monde(tmp_path, journal=[ev("lancee", minutes_avant=10, projet="demo")])
    faux = FauxExecuteur()
    assert aller(racine, ID, executer=faux) == 2
    assert "déjà en cours" in capsys.readouterr().err and faux.appels == []


def test_autre_mission_meme_projet_refusee(tmp_path, capsys):
    racine = monde(tmp_path, journal=[ev("lancee", mission=ID2, minutes_avant=10, projet="demo")])
    assert aller(racine, ID, executer=FauxExecuteur()) == 2
    assert "une seule mission à la fois par projet" in capsys.readouterr().err


def test_deux_noms_de_projet_meme_depot_comptent_pour_un(tmp_path, capsys):
    racine = monde(tmp_path, journal=[ev("lancee", mission=ID2, minutes_avant=10, projet="demo-bis")])
    assert aller(racine, ID, executer=FauxExecuteur()) == 2  # demo et demo-bis partagent git_root « demo »
    assert ID2 in capsys.readouterr().err


def test_autre_mission_autre_projet_autorisee(tmp_path):
    racine = monde(tmp_path, journal=[ev("lancee", mission=ID2, minutes_avant=10, projet="autre")])
    assert aller(racine, ID, executer=FauxExecuteur()) == 0


def test_journal_illisible_refuse_au_lieu_de_croire_qu_il_est_vide(tmp_path, capsys, monkeypatch):
    racine = monde(tmp_path)

    def illisible(_chemin):
        raise lm.commun.ErreurJournal("journal missions.jsonl illisible (PermissionError).")

    monkeypatch.setattr(lm.commun, "lire_journal", illisible)
    faux = FauxExecuteur()
    assert aller(racine, ID, executer=faux) == 2
    err = capsys.readouterr().err
    assert "illisible" in err and "Impossible de savoir" in err and faux.appels == []


def test_lignes_de_journal_abimees_sont_signalees(tmp_path, capsys):
    racine = monde(tmp_path)
    journal = racine / "donnees" / "missions.jsonl"
    journal.write_text("pas du json\n" + journal.read_text(encoding="utf-8"), encoding="utf-8")
    assert aller(racine, ID, executer=FauxExecuteur(), argv=["--dry-run"]) == 0
    assert "1 ligne(s) illisible(s) ignorée(s) (n° 1)" in capsys.readouterr().out


def test_stop_refuse(tmp_path, capsys):
    racine = monde(tmp_path)
    (racine / "donnees" / "STOP").write_text("", encoding="utf-8")
    faux = FauxExecuteur()
    assert aller(racine, ID, executer=faux) == 2
    assert "STOP" in capsys.readouterr().err and faux.appels == []


# ---------- plus de plafond « En cours » : Orion n'est jamais lu ----------
class LecteurInterdit:
    """Remplace le lecteur réel de `gh` : tout appel fait échouer le test."""

    def __call__(self, *a, **k):
        raise AssertionError("le lanceur ne doit jamais lire Orion")


@pytest.fixture
def sans_orion(monkeypatch):
    monkeypatch.setattr(lm.kanban, "executer_gh", LecteurInterdit())
    monkeypatch.setattr(lm.kanban, "lire_cartes", LecteurInterdit())
    monkeypatch.setattr(lm.kanban, "lire_json", LecteurInterdit())


def test_lancement_et_dry_run_ne_lisent_pas_orion(tmp_path, sans_orion):
    racine = monde(tmp_path)
    assert aller(racine, ID, argv=["--dry-run"]) == 0
    assert aller(racine, ID, executer=FauxExecuteur()) == 0
    (racine / "briefs" / f"{ID2}.md").write_text(brief(projet="autre"), encoding="utf-8")
    assert aller(racine, ID2, ID, executer=FauxExecuteur(), argv=["--parallele"]) == 0


def test_le_lanceur_n_a_plus_de_lecteur_de_cartes():
    assert not hasattr(lm, "lire_cartes_orion") and not hasattr(lm.Contexte, "max_en_cours")
    assert "lire_cartes" not in inspect.signature(lm.main).parameters


def test_cle_max_en_cours_ignoree_et_annoncee(tmp_path, capsys):
    racine = monde(tmp_path, defauts={"max_en_cours": 1})
    assert aller(racine, ID, executer=FauxExecuteur()) == 0
    assert "`defauts.max_en_cours` est ignoré" in capsys.readouterr().err


def test_sans_la_cle_max_en_cours_rien_n_est_annonce(tmp_path, capsys):
    assert aller(monde(tmp_path), ID, executer=FauxExecuteur()) == 0
    assert "max_en_cours" not in capsys.readouterr().err


# ---------- dry-run ----------
def test_dry_run_n_ecrit_rien_et_n_appelle_rien(tmp_path, capsys):
    racine = monde(tmp_path)
    faux = FauxExecuteur()
    avant = (racine / "donnees" / "missions.jsonl").read_text(encoding="utf-8")
    assert aller(racine, ID, executer=faux, argv=["--dry-run"]) == 0
    sortie_ = capsys.readouterr().out
    assert "[dry-run]" in sortie_ and "outils interdits" in sortie_ and "Bash(git push*)" in sortie_
    assert "variante : FR" in sortie_
    assert faux.appels == [] and not (racine / "briefs" / f"{ID}-compte-rendu.md").exists()
    assert (racine / "donnees" / "missions.jsonl").read_text(encoding="utf-8") == avant


def test_dry_run_copilot_affiche_les_avertissements(tmp_path, capsys):
    assert aller(monde(tmp_path), ID, argv=["--dry-run", "--moteur", "copilot"]) == 0
    assert "non testés" in capsys.readouterr().out


def test_dry_run_signale_un_refus(tmp_path, capsys):
    racine = monde(tmp_path, journal=[ev("lancee", mission=ID2, minutes_avant=10, projet="demo")])
    assert aller(racine, ID, argv=["--dry-run"]) == 2
    assert "REFUS" in capsys.readouterr().err


def test_config_absente(tmp_path, capsys):
    racine = tmp_path / "vide"
    racine.mkdir()
    assert lm.main([ID], racine=racine) == 2
    assert "config.json introuvable" in capsys.readouterr().err


# ---------- exécution ----------
def test_succes_journal_et_compte_rendu(tmp_path):
    racine = monde(tmp_path)
    faux = FauxExecuteur(sortie(result="## Fait\nTout.", cout=1.25, session="sid-9"))
    assert aller(racine, ID, executer=faux, git=FauxGit(head="aaaa1111")) == 0
    lignes = journal(racine)
    assert [e["evenement"] for e in lignes] == ["lancee", "terminee"]
    assert lignes[0]["variante"] == "FR" and lignes[0]["moteur"] == "claude" and lignes[0]["projet"] == "demo"
    assert lignes[1]["session_id"] == "sid-9" and "1.25 USD" in lignes[1]["note"]
    cr = compte_rendu(racine)
    assert "terminée" in cr and "## Fait\nTout." in cr and "session `sid-9`" in cr
    appel = faux.appels[0]
    assert appel["cwd"].endswith("backend") and appel["delai_s"] == 3600
    assert "Ajouter un export" in appel["entree"]


def test_echec_arret_budget_et_duree_max(tmp_path):
    cas = [
        (sortie(is_error=True, result="erreur"), "echouee"),
        (sortie(is_error=True, subtype="error_max_budget_usd", result="budget"), "arretee"),
        (sortie(expire=True, result=""), "arretee"),
    ]
    for i, (resultat, attendu) in enumerate(cas):
        racine = monde(tmp_path / str(i))
        assert aller(racine, ID, executer=FauxExecuteur(resultat)) == 1
        assert journal(racine)[-1]["evenement"] == attendu


def test_sortie_non_json_est_un_echec(tmp_path):
    racine = monde(tmp_path)
    assert aller(racine, ID, executer=FauxExecuteur(lm.Sortie("pas du json", "", False, 5.0, 0))) == 1
    assert journal(racine)[-1]["evenement"] == "echouee"


def test_lancement_impossible_est_journalise(tmp_path):
    racine = monde(tmp_path)
    assert aller(racine, ID, executer=FauxExecuteur(FileNotFoundError("claude"))) == 1
    assert "lancement impossible" in compte_rendu(racine) or journal(racine)[-1]["evenement"] == "echouee"


def test_refus_de_permission_listes(tmp_path):
    racine = monde(tmp_path)
    refus = [{"tool_name": "Bash", "tool_input": {"command": "git push"}}]
    assert aller(racine, ID, executer=FauxExecuteur(sortie(refus=refus))) == 0
    assert "Refus de permission : 1" in compte_rendu(racine) and "git push" in compte_rendu(racine)


def test_reference_distante_changee_est_signalee(tmp_path):
    racine = monde(tmp_path)
    git = FauxGit()

    def effet(_n):
        git.distant = "origine2"
        git.head = "cccc3333"

    faux = FauxExecuteur(sortie(), effet=effet)
    aller(racine, ID, executer=faux, git=git)
    assert "RÉFÉRENCE DISTANTE CHANGÉE" in compte_rendu(racine)
    assert "RÉFÉRENCE DISTANTE CHANGÉE" in journal(racine)[-1]["note"]
    assert "bbbb2222 feat: x" in compte_rendu(racine)


def test_projet_sans_git_pas_de_controle(tmp_path):
    racine = monde(tmp_path, texte=brief(projet="sansgit"))
    assert aller(racine, ID, executer=FauxExecuteur()) == 0
    assert "pas de dépôt suivi" in compte_rendu(racine)


def test_limite_d_usage_reessaie_puis_reussit(tmp_path):
    racine = monde(tmp_path)
    attentes = Attentes()
    faux = FauxExecuteur(sortie(is_error=True, result="usage limit reached", duree=5.0), sortie())
    assert aller(racine, ID, executer=faux, dormir=attentes) == 0
    assert attentes == [lm.LIMITE_ATTENTE_S] and len(faux.appels) == 2
    assert [e["evenement"] for e in journal(racine)] == ["lancee", "echouee", "lancee", "terminee"]


def test_limite_d_usage_abandonne_apres_trois_essais(tmp_path):
    racine = monde(tmp_path)
    attentes = Attentes()
    faux = FauxExecuteur(sortie(is_error=True, result="rate limit", duree=5.0))
    assert aller(racine, ID, executer=faux, dormir=attentes) == 1
    assert len(attentes) == lm.LIMITE_ESSAIS and len(faux.appels) == lm.LIMITE_ESSAIS + 1


def test_compte_rendu_existant_archive(tmp_path):
    racine = monde(tmp_path)
    (racine / "briefs" / f"{ID}-compte-rendu.md").write_text("ancien", encoding="utf-8")
    aller(racine, ID, executer=FauxExecuteur(sortie(result="nouveau")))
    archives = list((racine / "briefs").glob(f"{ID}-compte-rendu.2*.md"))
    assert len(archives) == 1 and archives[0].read_text(encoding="utf-8") == "ancien"
    assert "nouveau" in compte_rendu(racine)


def test_interruption_clavier_est_journalisee(tmp_path):
    racine = monde(tmp_path)
    with pytest.raises(KeyboardInterrupt):
        aller(racine, ID, executer=FauxExecuteur(KeyboardInterrupt()))
    assert journal(racine)[-1]["evenement"] == "arretee"


# ---------- chaîne et parallélisme ----------
def test_chaine_s_arrete_a_la_premiere_non_terminee(tmp_path, capsys):
    racine = monde(tmp_path)
    (racine / "briefs" / f"{ID2}.md").write_text(brief(projet="autre"), encoding="utf-8")
    faux = FauxExecuteur(sortie(is_error=True, result="échec"))
    assert aller(racine, ID, ID2, executer=faux) == 1
    assert len(faux.appels) == 1 and "Chaîne arrêtée" in capsys.readouterr().out


def test_chaine_enchaine_sans_chevauchement(tmp_path):
    racine = monde(tmp_path)
    (racine / "briefs" / f"{ID2}.md").write_text(brief(projet="autre"), encoding="utf-8")
    faux = FauxExecuteur()
    assert aller(racine, ID, ID2, executer=faux) == 0
    assert len(faux.appels) == 2 and not faux.chevauchement


def test_parallele_projets_differents(tmp_path, capsys):
    racine = monde(tmp_path)
    (racine / "briefs" / f"{ID2}.md").write_text(brief(projet="autre"), encoding="utf-8")
    faux = FauxExecuteur()
    assert aller(racine, ID, ID2, executer=faux, argv=["--parallele"]) == 0
    sortie_ = capsys.readouterr().out
    assert len(faux.appels) == 2 and "Bilan" in sortie_ and f"[{ID}]" in sortie_
    evenements = [(e["mission"], e["evenement"]) for e in journal(racine)]
    assert (ID, "terminee") in evenements and (ID2, "terminee") in evenements


def test_parallele_meme_projet_refuse_avant_tout_lancement(tmp_path, capsys):
    racine = monde(tmp_path)
    (racine / "briefs" / f"{ID2}.md").write_text(brief(projet="demo-bis"), encoding="utf-8")
    faux = FauxExecuteur()
    assert aller(racine, ID, ID2, executer=faux, argv=["--parallele"]) == 2
    assert "visent le même projet" in capsys.readouterr().err and faux.appels == []


def test_parallele_dry_run_montre_le_conflit(tmp_path, capsys):
    racine = monde(tmp_path)
    (racine / "briefs" / f"{ID2}.md").write_text(brief(projet="demo-bis"), encoding="utf-8")
    assert aller(racine, ID, ID2, argv=["--parallele", "--dry-run"]) == 2
    assert "CONFLIT" in capsys.readouterr().out


def test_parallele_une_mission_en_erreur_n_arrete_pas_les_autres(tmp_path):
    racine = monde(tmp_path)
    (racine / "briefs" / f"{ID2}.md").write_text(brief(projet="autre"), encoding="utf-8")

    def effet(numero):
        if numero == 1:
            raise RuntimeError("boum")

    # l'exécuteur lève dans la première mission : elle est journalisée « echouee », l'autre se termine
    faux = FauxExecuteur(sortie(), effet=effet)
    assert aller(racine, ID, ID2, executer=faux, argv=["--parallele"]) == 1
    fins = {e["mission"]: e["evenement"] for e in journal(racine) if e["evenement"] != "lancee"}
    assert sorted(fins.values()) == ["echouee", "terminee"]


def test_la_meme_mission_citee_deux_fois(tmp_path, capsys):
    assert aller(monde(tmp_path), ID, ID) == 2
    assert "deux fois" in capsys.readouterr().err


def test_conflits_du_lot_unitaire():
    def plan(m, projet, cle):
        return lm.Plan(m, "", "c", projet, None, "sonnet", "high", 2, 10, 3, "x", "/c", None, [], [], cle=cle)

    assert lm.conflits_du_lot([plan("a", "p1", "k1"), plan("b", "p2", "k2")]) == []
    assert len(lm.conflits_du_lot([plan("a", "p1", "k1"), plan("b", "p2", "k1")])) == 1


def test_cle_projet_normalisee():
    assert lm.cle_projet("/a/b", "/a") == lm.cle_projet("/a/b", "/a/")
    assert lm.cle_projet("/a/b", None) != lm.cle_projet("/a/c", None)


# ---------- environnement de la mission (débogueur hérité) ----------
def test_nettoyer_environnement_retire_bun_inspect_et_garde_le_reste():
    env = {"PATH": "/usr/bin", "BUN_INSPECT": "ws://127.0.0.1:9228/", "bun_inspect_connect_to": "x", "CLAUDE_X": "1"}
    propre, retraits = lm.nettoyer_environnement(env)
    assert propre == {"PATH": "/usr/bin", "CLAUDE_X": "1"}
    assert retraits == ["BUN_INSPECT", "bun_inspect_connect_to"]
    assert "BUN_INSPECT" in env  # l'original n'est pas modifié


@pytest.mark.parametrize(
    ("avant", "apres"),
    [
        ("--inspect", None),
        ("--inspect-brk=9229 --max-old-space-size=4096", "--max-old-space-size=4096"),
        ("--max-old-space-size=4096 --inspect=127.0.0.1:9229", "--max-old-space-size=4096"),
        ("--inspect-port 9229 --use-openssl-ca", "--use-openssl-ca"),
        ("--use-openssl-ca", "--use-openssl-ca"),
    ],
)
def test_nettoyer_environnement_node_options(avant, apres):
    propre, retraits = lm.nettoyer_environnement({"NODE_OPTIONS": avant})
    assert propre.get("NODE_OPTIONS") == apres
    assert bool(retraits) == (avant != apres)


def test_nettoyer_environnement_sans_debogueur_ne_retire_rien():
    env = {"PATH": "/usr/bin", "NODE_OPTIONS": "--use-openssl-ca"}
    assert lm.nettoyer_environnement(env) == (env, [])


def test_executer_processus_transmet_un_environnement_nettoye(monkeypatch, tmp_path):
    monkeypatch.setenv("BUN_INSPECT", "ws://127.0.0.1:9228/")
    monkeypatch.setenv("NODE_OPTIONS", "--inspect-brk --use-openssl-ca")
    monkeypatch.setenv("CLAUDE_CODE_AUTRE", "garde")
    vus = {}

    class FauxProcessus:
        pid, returncode = 1, 0

        def communicate(self, entree=None, timeout=None):
            return "{}", ""

    def faux_popen(commande, **options):
        vus.update(options)
        return FauxProcessus()

    monkeypatch.setattr(subprocess, "Popen", faux_popen)
    lm.executer_processus(["claude", "-p"], str(tmp_path), "brief", 5)
    env = vus["env"]
    assert not any(k.upper().startswith("BUN_INSPECT") for k in env)
    assert env["NODE_OPTIONS"] == "--use-openssl-ca"
    assert env["CLAUDE_CODE_AUTRE"] == "garde"
    assert "BUN_INSPECT" in os.environ  # l'environnement du lanceur reste intact


def test_dry_run_signale_les_variables_de_debogueur_retirees(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("BUN_INSPECT", "ws://127.0.0.1:9228/")
    assert aller(monde(tmp_path), ID, argv=["--dry-run"]) == 0
    sortie_ = capsys.readouterr().out
    assert "variables de débogueur retirées" in sortie_ and "BUN_INSPECT" in sortie_


def test_dry_run_sans_debogueur_ne_dit_rien_de_l_environnement(tmp_path, capsys, monkeypatch):
    for nom in ("BUN_INSPECT", "BUN_INSPECT_CONNECT_TO", "BUN_INSPECT_NOTIFY", "NODE_OPTIONS"):
        monkeypatch.delenv(nom, raising=False)
    assert aller(monde(tmp_path), ID, argv=["--dry-run"]) == 0
    assert "débogueur" not in capsys.readouterr().out


# ---------- pied de prompt ----------
@pytest.mark.parametrize("moteur", ["claude", "copilot"])
def test_le_pied_de_prompt_liste_les_colonnes_du_kanban(tmp_path, moteur):
    racine = monde(tmp_path)
    plan = lm.preparer(ID, racine, json.loads((racine / "config.json").read_text(encoding="utf-8")), moteur)
    assert "{colonnes}" not in plan.prompt
    for colonne in kanban.COLONNES:
        assert colonne in plan.prompt
    assert ", ".join(kanban.COLONNES) in plan.prompt
