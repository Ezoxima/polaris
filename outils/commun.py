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


class ErreurJournal(Exception):
    """Le journal existe mais n'a pas pu être lu (droits, disque, verrou) ; différent d'un journal absent."""


class Journal(list):
    """Événements valides du journal (c'est une liste de dict) ; `corrompues` : numéros (à partir de 1) des lignes
    non vides qui n'étaient pas un objet JSON, ignorées mais jamais sans trace."""

    corrompues: list[int]

    def __init__(self, evenements=(), corrompues=()):
        super().__init__(evenements)
        self.corrompues = list(corrompues)

    def avertissement(self) -> str | None:
        """Phrase à afficher quand des lignes ont été ignorées ; None s'il n'y en a pas."""
        if not self.corrompues:
            return None
        numeros = ", ".join(str(n) for n in self.corrompues[:10]) + (", …" if len(self.corrompues) > 10 else "")
        return f"journal : {len(self.corrompues)} ligne(s) illisible(s) ignorée(s) (n° {numeros})."


def lire_journal(chemin: Path) -> Journal:
    """Événements valides du journal.

    - journal absent : `Journal` vide (cas normal, avant la première mission) ;
    - journal présent mais illisible (erreur d'E/S) : lève ErreurJournal, jamais une liste vide qui ferait croire
      qu'aucune mission n'est en cours ;
    - ligne non vide qui n'est pas un objet JSON : ignorée mais comptée dans `Journal.corrompues`.
    """
    chemin = Path(chemin)
    try:
        lignes = chemin.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        return Journal()
    except OSError as e:
        raise ErreurJournal(f"journal {chemin.name} illisible ({type(e).__name__}).") from None
    evenements, corrompues = [], []
    for numero, ligne in enumerate(lignes, start=1):
        if not ligne.strip():
            continue
        try:
            e = json.loads(ligne)
        except ValueError:
            e = None
        if isinstance(e, dict):
            evenements.append(e)
        else:
            corrompues.append(numero)
    return Journal(evenements, corrompues)


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


SOURCE_MOTEUR_OPTION = "option --moteur"
SOURCE_MOTEUR_CONFIG = "config.json, `moteur_par_defaut`"
SOURCE_MOTEUR_DEFAUT = "défaut : moteur non configuré, `claude` par défaut (lance /configurer pour choisir)"


def choisir_moteur(option: str | None, config: dict[str, Any]) -> tuple[str, str]:
    """Moteur visé et sa SOURCE : `--moteur`, sinon `moteur_par_defaut` de config.json, sinon `claude` par défaut.

    Le défaut n'est jamais présenté comme un choix de l'utilisateur : la source est dite au dry-run et au journal."""
    if option:
        return option, SOURCE_MOTEUR_OPTION
    configure = config.get("moteur_par_defaut")
    if isinstance(configure, str) and configure.strip():
        return configure.strip(), SOURCE_MOTEUR_CONFIG
    return "claude", SOURCE_MOTEUR_DEFAUT
