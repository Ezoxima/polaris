"""Lecture de l'aide de Copilot (`copilot --help`) : fonctions pures, aucun appel de processus.

Partagé par le lanceur (`lancer_mission.py`) et l'inventaire des capacités (`capacites.py`). Les options et leurs
valeurs sont celles observées sur une version du CLI Copilot ; leur présence se lit dans le texte de l'aide, jamais
d'après le numéro de version.
"""

from __future__ import annotations

import re
from collections.abc import Callable
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
    versionnee: bool = False  # aide lue AVEC --no-auto-update et listant cette option : celle de la version lancée


class AideLue(NamedTuple):
    """Résultat de `lire_aide_versionnee` : le texte, et avec quelle commande il a été obtenu.

    `avec_option` vrai = lu par `--no-auto-update --help` et l'aide liste `--no-auto-update` : c'est l'aide de la
    version qui sera réellement lancée, et la mission passera l'option. Faux = repli sur `--help` seul (ou aide non
    lue, `cause` dit pourquoi) : la mission ne passe pas `--no-auto-update`."""

    texte: str = ""
    avec_option: bool = False
    cause: str = ""


def _texte_aide(lire: Callable[[list[str]], tuple[int, str]], args: list[str]) -> tuple[str, str]:
    """(texte, cause) ; texte vide et cause renseignée si la commande lève, sort en erreur ou ne dit rien."""
    try:
        code, texte = lire(args)
    except Exception as e:  # noqa: BLE001 — l'échec devient une cause écrite
        return "", type(e).__name__
    if code != 0:
        return "", f"code de sortie {code}"
    if not texte or not texte.strip():
        return "", "sortie vide"
    return texte, ""


def lire_aide_versionnee(lire: Callable[[list[str]], tuple[int, str]]) -> AideLue:
    """Lit l'aide de la version qui sera lancée. `lire(args)` renvoie (code de sortie, texte) ou lève.

    Deux versions installées côte à côte peuvent avoir des aides différentes : on lit d'abord
    `--no-auto-update --help`. Si cette aide liste `--no-auto-update`, c'est celle de la version lancée (la mission
    passera l'option). Sinon (option inconnue, erreur, sortie vide), repli sur `--help` seul, et la mission ne passe
    pas l'option : on ne transmet jamais une option dont la version lancée n'a pas confirmé l'existence."""
    texte, cause_option = _texte_aide(lire, ["--no-auto-update", "--help"])
    if texte and "--no-auto-update" in analyser_aide_copilot(texte).options:
        return AideLue(texte, True)
    texte_simple, cause = _texte_aide(lire, ["--help"])
    if texte_simple:
        return AideLue(texte_simple, False, cause_option or "l'aide lue avec l'option ne liste pas --no-auto-update")
    return AideLue("", False, cause or cause_option)


def analyser_aide_copilot(texte: str | None, avec_option: bool | None = None) -> AideCopilot:
    """Fonction pure : options suivies présentes dans le texte de `copilot --help`, et valeurs d'effort listées.

    Une option compte si elle apparaît telle quelle (pas comme préfixe d'une autre). Les valeurs d'effort sont lues
    dans le texte de l'option (liste entre crochets, parenthèses, ou après « choices ») ; seules celles que le
    lanceur connaît sont gardées. `avec_option` : l'aide a été lue avec `--no-auto-update` (None = on le déduit de la
    présence de l'option dans le texte, comportement d'un texte fourni sans précision)."""
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
    versionnee = (
        ("--no-auto-update" in options) if avec_option is None else (avec_option and "--no-auto-update" in options)
    )
    return AideCopilot(True, options, efforts, _documente_auto(texte), versionnee)


def _documente_auto(texte: str) -> bool:
    """Vrai si le texte de l'option `--model` cite la valeur `auto` (entre guillemets ou en mot isolé).

    Seul ce texte compte : `--no-auto-update` ou un « auto » ailleurs dans l'aide ne prouvent rien."""
    m = re.search(_option("--model") + r"(?P<reste>.*?)(?=\n\s*-{1,2}[A-Za-z]|\Z)", texte, re.S)
    return bool(m and re.search(r"(?<![\w-])auto(?![\w-])", m["reste"], re.I))


def _option(nom: str) -> str:
    return r"(?<![\w-])" + re.escape(nom) + r"(?![\w-])"
