"""Tests d'hygiène du dépôt : liens, fichiers vides, reste de travail, fichiers privés non suivis, outils communs."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import date
from pathlib import Path

import pytest

import commun
import nouvel_id

RACINE = Path(__file__).resolve().parent.parent
LIEN = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
BLOC_CODE = re.compile(r"```.*?```", re.S)


def suivis() -> list[Path]:
    sortie = subprocess.run(["git", "-C", str(RACINE), "ls-files", "-z"], capture_output=True, check=True).stdout
    return [RACINE / n for n in sortie.decode("utf-8").split("\0") if n]


def documents() -> list[Path]:
    return [p for p in suivis() if p.suffix == ".md"]


# ---------- liens ----------
@pytest.mark.parametrize("doc", documents(), ids=lambda p: p.relative_to(RACINE).as_posix())
def test_liens_relatifs_valides(doc):
    texte = BLOC_CODE.sub("", doc.read_text(encoding="utf-8"))
    morts = []
    for cible in LIEN.findall(texte):
        if re.match(r"^(https?:|mailto:|#)", cible):
            continue
        chemin = cible.split("#")[0]
        if chemin and not (doc.parent / chemin).resolve().exists():
            morts.append(cible)
    assert morts == [], f"liens morts dans {doc.relative_to(RACINE)} : {morts}"


# ---------- hygiène ----------
def test_aucun_fichier_vide():
    vides = [p.relative_to(RACINE).as_posix() for p in suivis() if p.stat().st_size == 0]
    assert vides == []


def test_pas_de_reste_de_travail_a_faire():
    marqueurs = re.compile(r"\b(TODO|FIXME|XXX|WIP)\b")
    trouves = []
    for p in suivis():
        if p.suffix in {".md", ".py", ".json", ".toml", ".yml", ".jsonl"} and p.name != "test_depot.py":
            if marqueurs.search(p.read_text(encoding="utf-8")):
                trouves.append(p.relative_to(RACINE).as_posix())
    assert trouves == []


def test_les_fichiers_prives_ne_sont_pas_suivis():
    noms = {p.relative_to(RACINE).as_posix() for p in suivis()}
    assert "config.json" not in noms and ".env" not in noms
    assert not any(n.startswith("briefs/") for n in noms)
    donnees = {n for n in noms if n.startswith("donnees/")}
    assert donnees == {"donnees/echeances.exemple.json", "donnees/veille-taches.exemple.json"}
    assert {n for n in noms if n.startswith("memoire/")} == {"memoire/INDEX.md"}


def test_les_exemples_sont_du_json_valide():
    for nom in ("config.exemple.json", "donnees/echeances.exemple.json", "donnees/veille-taches.exemple.json"):
        json.loads((RACINE / nom).read_text(encoding="utf-8"))


def test_la_config_exemple_ne_contient_aucun_tableau_ni_secret():
    cfg = json.loads((RACINE / "config.exemple.json").read_text(encoding="utf-8"))
    assert cfg["kanban"]["numero"] is None and cfg["kanban"]["projet_id"] == "" and cfg["kanban"]["champs"] == {}
    assert all(v == "" for v in cfg["copilot"]["modeles"].values())


def test_licence_mit_au_nom_de_l_auteur():
    texte = (RACINE / "LICENSE").read_text(encoding="utf-8")
    assert texte.startswith("MIT License") and "Copyright (c) 2026 Gwenael Cochet" in texte


def test_aucune_dependance_a_l_execution():
    texte = (RACINE / "pyproject.toml").read_text(encoding="utf-8")
    assert "dependencies = []" in texte and 'requires-python = ">=3.11"' in texte


def test_les_outils_n_importent_que_la_bibliotheque_standard():
    locaux = {p.stem for p in (RACINE / "outils").glob("*.py")}
    autorises = set(__import__("sys").stdlib_module_names) | locaux
    for p in (RACINE / "outils").glob("*.py"):
        for ligne in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)", ligne)
            if m:
                assert m[1] in autorises, f"{p.name} importe {m[1]}, absent de la bibliothèque standard"


def test_agents_md_reste_court():
    lignes = (RACINE / "AGENTS.md").read_text(encoding="utf-8").splitlines()
    assert len(lignes) <= 80  # chargé à chaque session : chaque ligne coûte


def test_preferences_existent_et_agents_md_y_renvoie():
    prefs = (RACINE / "registre" / "preferences.md").read_text(encoding="utf-8")
    assert re.search(r"^## Interdits ajoutés$", prefs, re.M)
    agents = (RACINE / "AGENTS.md").read_text(encoding="utf-8")
    assert "registre/preferences.md" in agents and "ne lève aucun garde-fou du socle" in agents


def test_guide_poste_restreint_est_lie_et_complet():
    guide = (RACINE / "docs" / "installation-restreinte.md").read_text(encoding="utf-8")
    for titre in (
        "Inventaire",
        "Python hors du PATH",
        "sans Git",
        "Sans CLI",
        "Kanban",
        "Accords distincts",
        "Confidentialité",
    ):
        assert titre in guide, titre
    for source in ("README.md", "docs/installation.md"):
        assert "installation-restreinte.md" in (RACINE / source).read_text(encoding="utf-8")


def test_questions_par_tour_reglees_dans_les_preferences_et_lues_par_creuser():
    prefs = (RACINE / "registre" / "preferences.md").read_text(encoding="utf-8")
    assert re.search(r"Questions par tour.*: \*\*1\*\*", prefs)
    creuser = (RACINE / "commandes" / "creuser.md").read_text(encoding="utf-8")
    assert "registre/preferences.md" in creuser and "Questions par\n  tour" in creuser.replace("\r\n", "\n")


def test_version_du_changelog_et_de_pyproject_concordent():
    pyproject = (RACINE / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^version = "([^"]+)"', pyproject, re.M)[1]
    premiere = re.search(r"^## \[(\d+\.\d+\.\d+)\]", (RACINE / "CHANGELOG.md").read_text(encoding="utf-8"), re.M)[1]
    assert version == premiere == "0.3.0"


def test_plus_de_plafond_en_cours_dans_l_exemple_ni_les_registres():
    cfg = json.loads((RACINE / "config.exemple.json").read_text(encoding="utf-8"))
    assert "max_en_cours" not in cfg["defauts"]
    prefs = (RACINE / "registre" / "preferences.md").read_text(encoding="utf-8")
    assert "max_en_cours" not in prefs and "3 cartes" not in prefs


def test_grille_ne_promet_plus_de_modele_par_defaut_pour_copilot():
    grille = (RACINE / "registre" / "grille.md").read_text(encoding="utf-8")
    assert "refus" in grille and "--reasoning-effort" in grille and "credits_ia_max" in grille
    assert "utilise son modèle par défaut" not in grille


def test_regle_des_registres_locaux_dans_agents_et_copilot():
    agents = (RACINE / "AGENTS.md").read_text(encoding="utf-8")
    assert "## Registres locaux" in agents and "registre/X.local.md" in agents and "remplace entièrement" in agents
    copilot = (RACINE / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
    assert "registre/X.local.md" in copilot


def test_toute_commande_citant_un_registre_mentionne_la_regle_locale():
    for fichier in sorted((RACINE / "commandes").glob("*.md")):
        texte = fichier.read_text(encoding="utf-8")
        if re.search(r"`registre/\w+\.md`", texte):
            assert "sa version `.local.md`, voir AGENTS.md" in texte, fichier.name


def test_requirements_dev_epingles_et_utilises_par_la_ci():
    lignes = (RACINE / "requirements-dev.txt").read_text(encoding="utf-8").splitlines()
    paquets = [ligne for ligne in lignes if ligne.strip() and not ligne.lstrip().startswith("#")]
    assert {p.split("==")[0] for p in paquets} == {"pytest", "ruff"}
    assert all(re.fullmatch(r"[A-Za-z0-9_.-]+==\d+(\.\d+)*", p) for p in paquets)
    ci = (RACINE / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "pip install -r requirements-dev.txt" in ci


def test_pyproject_n_a_pas_de_second_jeu_de_versions_de_developpement():
    assert "optional-dependencies" not in (RACINE / "pyproject.toml").read_text(encoding="utf-8")


# ---------- commun ----------
def test_charger_config_messages_utiles(tmp_path):
    with pytest.raises(commun.ErreurConfig, match="config.exemple.json"):
        commun.charger_config(tmp_path)
    (tmp_path / "config.json").write_text("{pas du json", encoding="utf-8")
    with pytest.raises(commun.ErreurConfig, match="JSON invalide"):
        commun.charger_config(tmp_path)
    (tmp_path / "config.json").write_text("[1]", encoding="utf-8")
    with pytest.raises(commun.ErreurConfig, match="objet JSON"):
        commun.charger_config(tmp_path)
    (tmp_path / "config.json").write_text('{"a": 1}', encoding="utf-8")
    assert commun.charger_config(tmp_path) == {"a": 1}


def test_lire_ts_et_iso():
    t = commun.lire_ts("2026-11-25T10:00:00Z")
    assert commun.iso(t) == "2026-11-25T10:00:00Z"
    assert commun.lire_ts("2026-11-25T10:00:00").tzinfo is not None
    assert commun.lire_ts("n'importe quoi") is None and commun.lire_ts(5) is None


def test_lire_journal_compte_et_signale_les_lignes_corrompues(tmp_path):
    f = tmp_path / "j.jsonl"
    f.write_text('{"a": 1}\npas du json\n\n[1]\n{"b": 2}\n', encoding="utf-8")
    j = commun.lire_journal(f)
    assert j == [{"a": 1}, {"b": 2}] and j.corrompues == [2, 4]  # la ligne vide n'est pas une corruption
    assert "2 ligne(s)" in j.avertissement() and "2, 4" in j.avertissement()


def test_lire_journal_sain_n_a_pas_d_avertissement(tmp_path):
    f = tmp_path / "j.jsonl"
    f.write_text('{"a": 1}\n', encoding="utf-8")
    assert commun.lire_journal(f).avertissement() is None


def test_lire_journal_absent_donne_une_liste_vide(tmp_path):
    j = commun.lire_journal(tmp_path / "absent.jsonl")
    assert j == [] and j.corrompues == []


def test_lire_journal_illisible_leve_une_erreur(tmp_path):
    with pytest.raises(commun.ErreurJournal, match="illisible"):
        commun.lire_journal(tmp_path)  # un dossier : erreur d'E/S, pas un journal absent


# ---------- nouvel_id ----------
def test_reserver_cree_un_brief_vide_unique(tmp_path):
    jour = date(2026, 11, 25)
    a, b = nouvel_id.reserver(tmp_path, jour), nouvel_id.reserver(tmp_path, jour)
    assert re.fullmatch(r"m-20261125-01-[0-9a-f]{4}", a) and re.fullmatch(r"m-20261125-02-[0-9a-f]{4}", b)
    assert (tmp_path / "briefs" / f"{a}.md").read_text(encoding="utf-8") == ""
    assert nouvel_id.reserver(tmp_path, date(2026, 11, 26)).startswith("m-20261126-01-")


def test_nouvel_id_main(tmp_path, capsys):
    assert nouvel_id.main(["--nb", "2"], racine=tmp_path) == 0
    assert len(capsys.readouterr().out.split()) == 2
    assert nouvel_id.main(["--nb", "0"], racine=tmp_path) == 2


def test_instructions_copilot_renvoient_a_agents_md_et_restent_courtes():
    texte = (RACINE / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
    assert "AGENTS.md" in texte and "git push" in texte
    assert len(texte.splitlines()) <= 30


def test_la_config_exemple_signale_ses_projets_fictifs_et_les_reglages_copilot():
    cfg = json.loads((RACINE / "config.exemple.json").read_text(encoding="utf-8"))
    assert "fictifs" in cfg["_commentaire"]
    assert cfg["copilot"]["credits_ia_max"] is None and cfg["copilot"]["autoriser_tous_outils"] is False
    assert all(isinstance(v, dict) for v in cfg["projets"].values())


def test_la_doc_copilot_cite_les_options_observees_et_les_garde_fous():
    doc = (RACINE / "docs" / "copilot.md").read_text(encoding="utf-8")
    for option in ("--reasoning-effort", "--max-ai-credits", "--usage-output-file", "--allow-all-tools"):
        assert option in doc
    assert "Application seule" in doc and "pas des USD" in doc
    assert "autoriser_tous_outils" in (RACINE / "docs" / "garde-fous.md").read_text(encoding="utf-8")


def test_configurer_pose_une_question_a_la_fois_et_n_ecrit_qu_apres_accord():
    texte = (RACINE / "commandes" / "configurer.md").read_text(encoding="utf-8")
    for attendu in (
        "Une seule question à la fois",
        "Rien n'est écrit sans mon accord",
        "diff exact",
        "python outils/capacites.py",
        "« non testé » n'est pas « disponible »",
        "Aucune carte n'est créée ni migrée",
        "kanban.mode",
        "voie_preferee",
        "--model auto",
        "Une valeur vide est refusée",
    ):
        assert attendu in texte, attendu
    for section in ("inventaire", "projets", "kanban", "voie", "modeles"):
        assert f"({section})".replace("(", "(`").replace(")", "`)") in texte or f"`{section}`" in texte, section


def test_go_et_lancer_proposent_la_voie_et_ne_basculent_jamais_seuls():
    for nom in ("go", "lancer"):
        texte = " ".join(
            (RACINE / "commandes" / f"{nom}.md").read_text(encoding="utf-8").replace("*", "").lower().split()
        )
        assert "python outils/capacites.py --voie" in texte and "--prompt" in texte, nom
        assert "jamais équivalente" in texte and "ne change jamais de voie" in texte, nom


def test_le_tableau_des_controles_de_l_architecture_est_celui_de_capacites():
    import capacites

    doc = (RACINE / "docs" / "architecture.md").read_text(encoding="utf-8")
    debut, fin = "<!-- debut tableau controles -->", "<!-- fin tableau controles -->"
    assert doc.count(debut) == doc.count(fin) == 1
    assert doc.split(debut)[1].split(fin)[0].strip() == capacites.tableau_controles()


def test_auto_est_la_regle_de_la_grille_et_plus_une_promesse():
    grille = (RACINE / "registre" / "grille.md").read_text(encoding="utf-8")
    assert "lot suivant" not in grille and "Stratégie `auto`" in grille and "currentModel" in grille
    doc = (RACINE / "docs" / "copilot.md").read_text(encoding="utf-8")
    assert "--model=auto" in doc and "non relevé" in doc and "--no-auto-update" in doc and "SetShouldExit" in doc


def test_l_accueil_configurer_est_l_etape_recommandee_des_guides_d_installation():
    assert "/configurer" in (RACINE / "docs" / "installation.md").read_text(encoding="utf-8")
    assert "capacites.py" in (RACINE / "docs" / "installation-restreinte.md").read_text(encoding="utf-8")


def test_le_readme_assume_les_limites_des_voies_sans_lanceur():
    readme = (RACINE / "README.md").read_text(encoding="utf-8")
    limites = readme.split("## Limites assumées")[1].split("## Feuille de route")[0]
    assert "Sous-session et prompt" in limites and "skills dans l'application Copilot" in limites
    assert "--allow-all-tools" in limites and "/parametrage" not in readme


def test_l_exemple_de_config_declare_la_voie_preferee_et_les_capacites():
    cfg = json.loads((RACINE / "config.exemple.json").read_text(encoding="utf-8"))
    assert cfg["voie_preferee"] == "cli" and cfg["capacites"] == {} and cfg["kanban"]["mode"] == "github"
