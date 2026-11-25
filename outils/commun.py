"""Fonctions partagées par les outils de Polaris : configuration, journal, horodatages, écriture atomique.

Bibliothèque standard seulement. Aucun appel réseau, aucun appel à `gh` ni à une IA.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RACINE = Path(__file__).resolve().parent.parent
NOM_CONFIG = "config.json"
NOM_CONFIG_EXEMPLE = "config.exemple.json"


class ErreurConfig(Exception):
    """`config.json` est absent, illisible ou incomplet ; le message dit quoi faire."""


def charger_config(racine: Path = RACINE) -> dict[str, Any]:
    """Lit `config.json` à la racine du dépôt ; lève ErreurConfig avec un message utile."""
    chemin = Path(racine) / NOM_CONFIG
    try:
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ErreurConfig(
            f"{NOM_CONFIG} introuvable : copie {NOM_CONFIG_EXEMPLE} en {NOM_CONFIG} puis adapte les chemins "
            "de tes projets (voir docs/installation.md)."
        ) from None
    except OSError as e:
        raise ErreurConfig(f"{NOM_CONFIG} illisible ({type(e).__name__}).") from None
    except ValueError as e:
        raise ErreurConfig(f"{NOM_CONFIG} : JSON invalide ({e}).") from None
    if not isinstance(donnees, dict):
        raise ErreurConfig(f"{NOM_CONFIG} : un objet JSON est attendu.")
    return donnees


def lire_journal(chemin: Path) -> list[dict]:
    """Lignes JSON valides du journal. Une ligne corrompue est ignorée ; un journal absent donne []."""
    try:
        lignes = Path(chemin).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    evenements = []
    for ligne in lignes:
        try:
            e = json.loads(ligne)
        except ValueError:
            continue
        if isinstance(e, dict):
            evenements.append(e)
    return evenements


def lire_ts(valeur: object) -> datetime | None:
    """Horodatage ISO 8601 vers datetime avec fuseau (UTC si absent) ; None si illisible."""
    if not isinstance(valeur, str):
        return None
    try:
        ts = datetime.fromisoformat(valeur.replace("Z", "+00:00"))
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


def iso(ts: datetime) -> str:
    """Datetime vers `2026-11-25T08:30:00Z` (UTC, sans fractions)."""
    return ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def ecrire_json_atomique(chemin: Path, objet: Any) -> None:
    """Écrit dans un fichier temporaire du même dossier puis remplace : jamais un fichier à moitié écrit."""
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    fd, temporaire = tempfile.mkstemp(prefix=chemin.name + ".", suffix=".tmp", dir=chemin.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(objet, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(temporaire, chemin)
    except BaseException:
        try:
            os.unlink(temporaire)
        except OSError:
            pass
        raise


def sortie_utf8() -> None:
    """Un terminal Windows en cp1252 ferait planter `print` sur un « — » : on force l'UTF-8."""
    for flux in (sys.stdout, sys.stderr):
        reconfigurer = getattr(flux, "reconfigure", None)
        if reconfigurer is not None:
            reconfigurer(encoding="utf-8", errors="replace")
