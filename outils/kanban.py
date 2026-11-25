"""Lecture d'Orion (le tableau GitHub Projects) via `gh`, partagée par le lanceur, la veille et l'initialisation.

Seule `executer_gh` appelle réellement `gh` ; elle est remplacée par un faux dans les tests. Toutes les lectures
utilisent `gh project item-list` ou `gh project list` : aucune écriture n'est faite d'ici.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from typing import Any, NamedTuple

COLONNES = ("À cadrer", "Prêt", "En cours", "En attente", "En pause", "Fait")
NATURES = ("Chantier", "Démarche", "Décision", "Script", "POC")
TAILLES = ("XS", "S", "M", "L", "XL")
PHASES = ("POC", "MVP", "Produit final")
LIMITE_CARTES = 500
DELAI_GH_S = 30


class Resultat(NamedTuple):
    """Résultat d'un appel à `gh`."""

    code: int
    sortie: str
    erreur: str = ""


Executeur = Callable[[list[str]], Resultat]


class ErreurGh(Exception):
    """Erreur attendue d'un appel à `gh` ; le message est court et ne contient jamais de jeton."""


def executer_gh(args: list[str]) -> Resultat:
    """Lance `gh` (seul endroit qui l'appelle). Lève FileNotFoundError si `gh` n'est pas installé."""
    executable = shutil.which("gh")
    if executable is None:
        raise FileNotFoundError("gh")
    fini = subprocess.run(
        [executable, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=DELAI_GH_S,
        stdin=subprocess.DEVNULL,
        cwd=tempfile.gettempdir(),
        check=False,
    )
    return Resultat(fini.returncode, fini.stdout, fini.stderr)


def appeler(executer: Executeur, args: list[str]) -> Resultat:
    """Appelle `gh` et traduit les pannes courantes en ErreurGh (message court, sans jeton)."""
    try:
        resultat = executer(list(args))
    except FileNotFoundError:
        raise ErreurGh("La commande « gh » est introuvable : installe GitHub CLI (https://cli.github.com).") from None
    except subprocess.TimeoutExpired:
        raise ErreurGh(f"Délai dépassé : gh n'a pas répondu en {DELAI_GH_S} s.") from None
    except OSError:
        raise ErreurGh("Impossible de lancer la commande « gh ».") from None
    return resultat


def lire_json(executer: Executeur, args: list[str]) -> Any:
    """Appelle `gh` et renvoie le JSON de sa sortie ; ErreurGh si l'appel échoue ou si la sortie est illisible."""
    resultat = appeler(executer, args)
    if resultat.code != 0:
        raise ErreurGh(
            f"gh a échoué (code {resultat.code}) : est-il connecté, avec le droit `project` ? (gh auth status)"
        )
    try:
        return json.loads(resultat.sortie)
    except (TypeError, ValueError):
        raise ErreurGh("Sortie de gh illisible (JSON attendu).") from None


def commande_lecture(config_kanban: dict) -> list[str]:
    """Arguments de `gh project item-list` pour le tableau de `config.json` ; ErreurGh si non configuré."""
    numero = config_kanban.get("numero")
    if not isinstance(numero, int) or isinstance(numero, bool):
        raise ErreurGh(
            "Kanban non configuré : lance `python outils/kanban_init.py` (clé `kanban.numero` de config.json)."
        )
    proprietaire = config_kanban.get("proprietaire") or "@me"
    return [
        "project",
        "item-list",
        str(numero),
        "--owner",
        str(proprietaire),
        "--format",
        "json",
        "--limit",
        str(LIMITE_CARTES),
    ]


def lire_cartes(executer: Executeur, config_kanban: dict) -> tuple[list[dict], bool]:
    """(cartes brutes, tronqué ?). ErreurGh avec un message court si la lecture échoue."""
    donnees = lire_json(executer, commande_lecture(config_kanban))
    total = None
    if isinstance(donnees, dict):
        total = donnees.get("totalCount")
        donnees = donnees.get("items")
    if not isinstance(donnees, list):
        raise ErreurGh("Sortie de gh inattendue (pas de liste de cartes).")
    cartes = [c for c in donnees if isinstance(c, dict)]
    return cartes, isinstance(total, int) and total > len(donnees)


def cartes_en_cours(cartes: list[dict]) -> list[dict]:
    """Cartes « En cours » (information seulement : aucune règle ni seuil n'en dépend)."""
    return [c for c in cartes if isinstance(c.get("status"), str) and c["status"].strip() == "En cours"]


def titre_carte(carte: dict) -> str:
    """Titre affichable d'une carte."""
    return str(carte.get("title") or "(sans titre)")
