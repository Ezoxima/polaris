"""Lecture de l'aide de Copilot (`copilot --help`) : fonctions pures, aucun appel de processus.

Partagé par le lanceur (`lancer_mission.py`) et l'inventaire des capacités (`capacites.py`). Les options et leurs
valeurs sont celles observées sur une version du CLI Copilot ; leur présence se lit dans le texte de l'aide, jamais
d'après le numéro de version.
"""

from __future__ import annotations

import re
from typing import NamedTuple

# Options de `copilot --help` que le lanceur sait utiliser (observées sur une version récente, jamais essayées en réel).
OPTIONS_COPILOT_SUIVIES = (
    "--reasoning-effort",
    "--max-ai-credits",
    "--usage-output-file",
    "--allow-all-tools",
    "--no-auto-update",
)
EFFORTS_COPILOT = ("low", "medium", "high")  # valeurs transmises quand l'aide ne liste pas de valeurs
EFFORTS_COPILOT_CONNUS = ("minimal", "low", "medium", "high", "xhigh", "max")


class AideCopilot(NamedTuple):
    """Ce que `copilot --help` annonce. `lue` faux = aide absente : aucune option facultative n'est transmise."""

    lue: bool = False
    options: frozenset = frozenset()
    efforts: tuple = ()  # valeurs listées pour --reasoning-effort ; () si l'aide n'en liste pas
    modele_auto: bool = False  # l'aide de --model documente la valeur « auto » (choix automatique du modèle)


def analyser_aide_copilot(texte: str | None) -> AideCopilot:
    """Fonction pure : options suivies présentes dans le texte de `copilot --help`, et valeurs d'effort listées.

    Une option compte si elle apparaît telle quelle (pas comme préfixe d'une autre). Les valeurs d'effort sont lues
    dans le texte de l'option (liste entre crochets, parenthèses, ou après « choices ») ; seules celles que le
    lanceur connaît sont gardées."""
    if not texte or not texte.strip():
        return AideCopilot()
    options = frozenset(o for o in OPTIONS_COPILOT_SUIVIES if re.search(_option(o), texte))
    efforts: tuple = ()
    m = re.search(_option("--reasoning-effort") + r"(?P<reste>.*?)(?=\n\s*-{1,2}[A-Za-z]|\Z)", texte, re.S)
    if m:
        candidats = re.findall(r"(?:choices?|values?|one of)\b\s*:?\s*([^\n]+)", m["reste"], re.I)
        candidats += re.findall(r"[\[(<{]([^\])>}\n]+)[\])>}]", m["reste"])
        for texte_liste in candidats:  # le premier groupe qui cite au moins deux efforts connus est la liste
            mots = re.findall(r"[a-z]+", texte_liste.lower())
            trouves = tuple(dict.fromkeys(x for x in mots if x in EFFORTS_COPILOT_CONNUS))
            if len(trouves) >= 2:
                efforts = trouves
                break
    return AideCopilot(True, options, efforts, _documente_auto(texte))


def _documente_auto(texte: str) -> bool:
    """Vrai si le texte de l'option `--model` cite la valeur `auto` (entre guillemets ou en mot isolé).

    Seul ce texte compte : `--no-auto-update` ou un « auto » ailleurs dans l'aide ne prouvent rien."""
    m = re.search(_option("--model") + r"(?P<reste>.*?)(?=\n\s*-{1,2}[A-Za-z]|\Z)", texte, re.S)
    return bool(m and re.search(r"(?<![\w-])auto(?![\w-])", m["reste"], re.I))


def _option(nom: str) -> str:
    return r"(?<![\w-])" + re.escape(nom) + r"(?![\w-])"
