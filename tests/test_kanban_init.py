"""Tests de `kanban_init` et du module partagé `kanban` : `gh` est SIMULÉ, aucun appel réel, rien n'est écrit sur GitHub.

Garde-fou : `kanban.executer_gh` et `subprocess.run` lèvent `AppelReel` tant qu'un test n'injecte pas son faux `gh`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

import commun
import kanban
import kanban_init as ki

RACINE_DEPOT = Path(__file__).resolve().parent.parent


class AppelReel(BaseException):
    pass


@pytest.fixture(autouse=True)
def aucun_appel_reel(monkeypatch):
    def interdit(*_a, **_k):
        raise AppelReel("appel réel pendant un test")

    monkeypatch.setattr(kanban, "executer_gh", interdit)
    monkeypatch.setattr(subprocess, "run", interdit)


class FauxGh:
    """Simule `gh project …` : un tableau neuf avec le champ Status par défaut, puis les champs qu'on lui crée."""

    def __init__(self, existants=(), echec_sur=None, sans_status=False, installe=True):
        self.existants = list(existants)
        self.echec_sur = echec_sur  # fragment de commande dont l'appel échoue
        self.sans_status = sans_status
        self.installe = installe
        self.appels = []
        self.crees = []
        self.status_remplace = False

    def _champs(self):
        champs = [{"id": "ID_TITRE", "name": "Title", "type": "ProjectV2Field"}]
        if not self.sans_status:
            options = kanban.COLONNES if self.status_remplace else ("Todo", "In Progress", "Done")
            champs.append(
                {
                    "id": "ID_STATUS",
                    "name": "Status",
                    "type": "ProjectV2SingleSelectField",
                    "options": [{"id": f"OPT_STATUS_{i}", "name": n} for i, n in enumerate(options)],
                }
            )
        for nom, options in self.crees:
            champ = {"id": f"ID_{nom}", "name": nom, "type": "X"}
            if options:
                champ["options"] = [{"id": f"OPT_{nom}_{i}", "name": o} for i, o in enumerate(options)]
            champs.append(champ)
        return champs

    def __call__(self, args):
        if not self.installe:
            raise FileNotFoundError("gh")
        self.appels.append(list(args))
        ligne = " ".join(args)
        if self.echec_sur and self.echec_sur in ligne:
            return kanban.Resultat(1, "", "HTTP 403 : insufficient scopes")
        if args[:2] == ["project", "list"]:
            return kanban.Resultat(0, json.dumps({"projects": [{"number": 3, "title": t} for t in self.existants]}))
        if args[:2] == ["project", "create"]:
            return kanban.Resultat(0, json.dumps({"number": 7, "id": "ID_PROJET", "url": "https://exemple.test/7"}))
        if args[:2] == ["project", "field-list"]:
            return kanban.Resultat(0, json.dumps({"fields": self._champs()}))
        if args[:2] == ["api", "graphql"]:
            self.status_remplace = True
            return kanban.Resultat(0, "{}")
        if args[:2] == ["project", "field-create"]:
            nom = args[args.index("--name") + 1]
            options = (
                args[args.index("--single-select-options") + 1].split(",") if "--single-select-options" in args else []
            )
            self.crees.append((nom, options))
            return kanban.Resultat(0, "{}")
        raise AssertionError(f"commande gh inattendue : {args}")


def depot(tmp_path, avec_config=False, config=None):
    """Racine temporaire avec config.exemple.json (copie de la vraie) et, au choix, un config.json."""
    shutil.copy(RACINE_DEPOT / commun.NOM_CONFIG_EXEMPLE, tmp_path / commun.NOM_CONFIG_EXEMPLE)
    if avec_config:
        (tmp_path / commun.NOM_CONFIG).write_text(json.dumps(config or {}), encoding="utf-8")
    return tmp_path


def config_ecrite(racine):
    return json.loads((racine / commun.NOM_CONFIG).read_text(encoding="utf-8"))


# ---------- dry-run ----------
def test_dry_run_ne_cree_rien_et_n_appelle_pas_gh(tmp_path, capsys):
    racine = depot(tmp_path)
    assert ki.main(["--dry-run"], racine=racine) == 0  # AppelReel si gh était appelé
    sortie = capsys.readouterr().out
    assert "[dry-run]" in sortie and "Rien n'est créé" in sortie
    assert "gh project create" in sortie and "À cadrer · Prêt · En cours · En attente · En pause · Fait" in sortie
    assert "Nature · Projet · Taille · Phase · Prochaine étape · % 5 h · % hebdo" in sortie
    assert not (racine / commun.NOM_CONFIG).exists()


def test_dry_run_avec_variante(tmp_path, capsys):
    assert ki.main(["--dry-run", "--avec-variante"], racine=depot(tmp_path)) == 0
    assert "Variante" in capsys.readouterr().out


def test_dry_run_refuse_si_la_config_a_deja_un_tableau(tmp_path, capsys):
    racine = depot(tmp_path, True, {"kanban": {"numero": 4, "projet_id": "ID_X"}})
    assert ki.main(["--dry-run"], racine=racine) == 2
    assert "contient déjà un tableau" in capsys.readouterr().err


# ---------- création ----------
def test_creation_complete_et_config_ecrite(tmp_path, capsys):
    racine = depot(tmp_path)
    gh = FauxGh()
    assert ki.main(["--proprietaire", "mon-compte", "--avec-variante"], racine=racine, executer=gh) == 0
    cfg = config_ecrite(racine)
    k = cfg["kanban"]
    assert k["numero"] == 7 and k["projet_id"] == "ID_PROJET" and k["proprietaire"] == "mon-compte"
    assert list(k["champs"]) == [
        "Status",
        "Nature",
        "Projet",
        "Taille",
        "Phase",
        "Prochaine étape",
        "% 5 h",
        "% hebdo",
        "Variante",
    ]
    assert list(k["champs"]["Status"]["options"]) == list(kanban.COLONNES)
    assert k["champs"]["Nature"]["options"]["POC"] == "OPT_Nature_4"
    assert k["champs"]["Projet"]["options"] == {}  # champ texte
    assert cfg["projets"]  # le reste de la config de l'exemple est conservé
    assert "Tableau « Orion » créé (numéro 7)" in capsys.readouterr().out


def test_mutation_status_contient_les_six_colonnes():
    mutation = ki.mutation_status("ID_STATUS")
    for colonne in kanban.COLONNES:
        assert f'name:"{colonne}"' in mutation
    assert 'fieldId:"ID_STATUS"' in mutation and "updateProjectV2Field" in mutation


def test_champs_crees_avec_les_bons_types(tmp_path):
    gh = FauxGh()
    ki.main([], racine=depot(tmp_path), executer=gh)
    assert dict(gh.crees)["Nature"] == list(kanban.NATURES)
    assert dict(gh.crees)["Taille"] == list(kanban.TAILLES)
    assert dict(gh.crees)["Phase"] == list(kanban.PHASES)
    creations = [a for a in gh.appels if a[:2] == ["project", "field-create"]]
    types = {a[a.index("--name") + 1]: a[a.index("--data-type") + 1] for a in creations}
    assert types["Projet"] == "TEXT" and types["% 5 h"] == "NUMBER" and types["Nature"] == "SINGLE_SELECT"


def test_n_efface_ni_ne_supprime_jamais(tmp_path):
    gh = FauxGh()
    ki.main([], racine=depot(tmp_path), executer=gh)
    interdit = ("delete", "close", "archive", "item-edit", "unlink")
    assert not any(any(mot in " ".join(a) for mot in interdit) for a in gh.appels)


def test_ecrit_dans_la_config_existante_sans_perdre_le_reste(tmp_path):
    racine = depot(tmp_path, True, {"moteur_par_defaut": "copilot", "projets": {"p": {"cwd": "p"}}})
    assert ki.main([], racine=racine, executer=FauxGh()) == 0
    cfg = config_ecrite(racine)
    assert (
        cfg["moteur_par_defaut"] == "copilot" and cfg["projets"] == {"p": {"cwd": "p"}} and cfg["kanban"]["numero"] == 7
    )


# ---------- refus ----------
def test_refuse_si_la_config_contient_deja_un_tableau(tmp_path, capsys):
    racine = depot(tmp_path, True, {"kanban": {"numero": 4}})
    gh = FauxGh()
    assert ki.main([], racine=racine, executer=gh) == 2
    assert gh.appels == [] and "contient déjà un tableau" in capsys.readouterr().err


def test_refuse_si_un_tableau_du_meme_titre_existe(tmp_path, capsys):
    racine = depot(tmp_path)
    gh = FauxGh(existants=["Autre", "Orion"])
    assert ki.main([], racine=racine, executer=gh) == 2
    assert "existe déjà (numéro 3)" in capsys.readouterr().err
    assert not any(a[:2] == ["project", "create"] for a in gh.appels)
    assert not (racine / commun.NOM_CONFIG).exists()


def test_titre_different_accepte(tmp_path):
    assert ki.main(["--titre", "Autre tableau"], racine=depot(tmp_path), executer=FauxGh(existants=["Orion"])) == 0


def test_gh_absent(tmp_path, capsys):
    assert ki.main([], racine=depot(tmp_path), executer=FauxGh(installe=False)) == 2
    assert "introuvable" in capsys.readouterr().err


def test_gh_sans_le_droit_project(tmp_path, capsys):
    assert ki.main([], racine=depot(tmp_path), executer=FauxGh(echec_sur="project list")) == 2
    assert "impossible de vérifier" in capsys.readouterr().err


# ---------- échec en cours de route ----------
def test_echec_de_creation_de_champ_dit_quel_tableau_est_incomplet(tmp_path, capsys):
    racine = depot(tmp_path)
    assert ki.main([], racine=racine, executer=FauxGh(echec_sur="--name Phase")) == 1
    err = capsys.readouterr().err
    assert "n°7" in err and "pas complet" in err and "ne supprime jamais rien" in err
    assert not (racine / commun.NOM_CONFIG).exists()  # rien d'écrit à moitié


def test_echec_de_la_mutation_status(tmp_path, capsys):
    assert ki.main([], racine=depot(tmp_path), executer=FauxGh(echec_sur="graphql")) == 1
    assert "Status" in capsys.readouterr().err


def test_tableau_sans_champ_status(tmp_path, capsys):
    assert ki.main([], racine=depot(tmp_path), executer=FauxGh(sans_status=True)) == 1
    assert "Status" in capsys.readouterr().err


# ---------- module kanban ----------
def test_commande_lecture_exige_un_tableau_configure():
    with pytest.raises(kanban.ErreurGh, match="non configuré"):
        kanban.commande_lecture({})
    args = kanban.commande_lecture({"numero": 7, "proprietaire": "moi"})
    assert args[:5] == ["project", "item-list", "7", "--owner", "moi"] and args[-2:] == ["--limit", "500"]
    assert kanban.commande_lecture({"numero": 7})[4] == "@me"


def test_lire_cartes_et_troncature():
    cartes = [{"title": "A"}, {"title": "B"}, "pas une carte"]

    def gh(_args):
        return kanban.Resultat(0, json.dumps({"totalCount": 9, "items": cartes}))

    lues, tronque = kanban.lire_cartes(gh, {"numero": 1})
    assert [c["title"] for c in lues] == ["A", "B"] and tronque is True


@pytest.mark.parametrize(
    "executeur,fragment",
    [
        (lambda a: kanban.Resultat(1, "", "non"), "gh a échoué"),
        (lambda a: kanban.Resultat(0, "pas du json"), "illisible"),
        (lambda a: kanban.Resultat(0, '{"items": 3}'), "inattendue"),
        (lambda a: (_ for _ in ()).throw(FileNotFoundError("gh")), "introuvable"),
        (lambda a: (_ for _ in ()).throw(subprocess.TimeoutExpired("gh", 30)), "Délai"),
        (lambda a: (_ for _ in ()).throw(OSError("x")), "Impossible"),
    ],
)
def test_lire_cartes_erreurs_courtes(executeur, fragment):
    with pytest.raises(kanban.ErreurGh, match=fragment):
        kanban.lire_cartes(executeur, {"numero": 1})


def test_cartes_en_cours_hors_poc_et_hors_carte_de_la_mission():
    cartes = [
        {"title": "A", "status": "En cours", "nature": "Chantier"},
        {"title": "B", "status": "En cours", "nature": "POC"},
        {"title": " c ", "status": "En cours"},
        {"title": "D", "status": "Prêt"},
    ]
    assert [c["title"] for c in kanban.cartes_en_cours(cartes)] == ["A", " c "]
    assert [c["title"] for c in kanban.cartes_en_cours(cartes, "C")] == ["A"]
