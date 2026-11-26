"""Inventaire des capacités de ce poste : qu'est-ce qui est disponible, indisponible ou non testé.

Usage (depuis la racine du dépôt) :

    python outils/capacites.py                                  # affiche l'inventaire (dry-run : n'écrit rien)
    python outils/capacites.py --ecrire                         # met à jour la section `capacites` de config.json
    python outils/capacites.py --declarer sous_session=disponible[:note]   # déclare à la main (avec --ecrire)
    python outils/capacites.py --voie [--moteur claude|copilot] # propose la voie de lancement et ses contrôles

Capacités : `cli_claude`, `cli_copilot`, `gh`, `gh_auth`, `git`, `python`, `sous_session`, `taches_planifiees`.
États : `disponible`, `indisponible`, `non_teste` (avec date et note).

Règles (aucune capacité n'est déclarée « disponible » sur un échec avalé) :

- la détection se limite à la présence de l'exécutable dans le PATH et à `--version` / `--help`, **locaux** (aucun
  appel de service) ; absent du PATH = `indisponible` ; toute autre difficulté (commande qui échoue, délai dépassé,
  sortie vide, script `.ps1`) = `non_teste`, avec la cause dans la note, jamais `disponible` ;
- `gh_auth` est toujours `non_teste` : vérifier l'authentification contacte le service ;
- `sous_session` et `taches_planifiees` sont **déclaratives** : aucune détection locale n'est possible, elles restent
  `non_teste` tant que l'utilisateur ne les a pas déclarées ;
- une capacité déclarée à la main (`source: declaree`) n'est **jamais** écrasée par la détection ;
- `--ecrire` ne modifie que la clé `capacites` de `config.json` (écriture atomique) et ne crée jamais `config.json`.

Pour `copilot`, l'aide est lue d'abord avec `--no-auto-update --help` : si cette aide liste `--no-auto-update`, c'est
celle de la version qui sera lancée et `--version` reçoit aussi l'option (c'est celle que le lanceur transmet) ; sinon
repli sur `--help` seul et `--version` est lu sans l'option (même règle que le lanceur, `aide_copilot.py`).

Aucun appel réel dans les tests : l'exécuteur local, `which` et l'horloge sont injectés.
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import commun
from aide_copilot import AideCopilot, analyser_aide_copilot, lire_aide_versionnee

DISPONIBLE, INDISPONIBLE, NON_TESTE = "disponible", "indisponible", "non_teste"
ETATS = (DISPONIBLE, INDISPONIBLE, NON_TESTE)
SOURCE_DETECTION, SOURCE_DECLAREE = "detection", "declaree"
CAPACITES = (
    "cli_claude",
    "cli_copilot",
    "gh",
    "gh_auth",
    "git",
    "python",
    "sous_session",
    "taches_planifiees",
)
EXECUTABLES = {"cli_claude": "claude", "cli_copilot": "copilot", "gh": "gh", "git": "git"}
DECLARATIVES = {
    "sous_session": "déclarative : la plateforme qui ouvre une session avec un prompt ne se détecte pas localement",
    "taches_planifiees": "déclarative : la planification de tâches ne se détecte pas localement",
}
PYTHON_MINI = (3, 11)
DELAI_LOCAL_S = 15
LIMITE_NOTE = 300

VOIES = ("cli", "sous_session", "prompt")
CONTROLES = ("verrou_projet", "duree_max", "journal_auto", "permissions", "releve_conso", "arret_urgence")
LIBELLES_CONTROLES = {
    "verrou_projet": "verrou par projet (une mission à la fois)",
    "duree_max": "durée max",
    "journal_auto": "journal automatique",
    "permissions": "permissions (liste d'outils)",
    "releve_conso": "relevé de consommation",
    "arret_urgence": "arrêt d'urgence donnees/STOP",
}
# (garantie, détail) par voie et par contrôle. « oui » = appliqué par le lanceur ; « non » = à faire à la main.
GARANTIES: dict[str, dict[str, tuple[str, str]]] = {
    "cli": {
        "verrou_projet": ("oui", "refus si une autre mission est en cours sur le même projet"),
        "duree_max": ("oui", "arrêt de l'arbre de processus à la durée du brief"),
        "journal_auto": ("oui", "`lancee`, puis `terminee`, `echouee` ou `arretee`"),
        "permissions": ("oui", "liste d'outils autorisés et interdits passée en ligne de commande"),
        "releve_conso": (
            "partiel",
            "Claude : coût lu ; Copilot : fichier d'usage si l'option existe, format non garanti",
        ),
        "arret_urgence": ("oui", "plus aucune nouvelle mission ne démarre ; celle en cours finit"),
    },
    "sous_session": {
        "verrou_projet": ("non", "rien n'empêche deux missions sur le même projet : vérifie à la main"),
        "duree_max": ("non", "aucun arrêt automatique : surveille la session"),
        "journal_auto": ("non", "seule `preparee` est écrite ; lancement et fin sont à noter à la main"),
        "permissions": ("non", "réglages de la plateforme, pas la liste d'outils de Polaris"),
        "releve_conso": ("non", "à relever à la main"),
        "arret_urgence": ("non", "`donnees/STOP` n'est lu que par le lanceur"),
    },
    "prompt": {
        "verrou_projet": ("non", "rien n'empêche deux missions sur le même projet : vérifie à la main"),
        "duree_max": ("non", "aucun arrêt automatique : surveille la session"),
        "journal_auto": ("non", "seule `preparee` est écrite ; lancement et fin sont à noter à la main"),
        "permissions": ("non", "réglages de la session où tu colles le prompt, pas la liste d'outils de Polaris"),
        "releve_conso": ("non", "à relever à la main"),
        "arret_urgence": ("non", "`donnees/STOP` n'est lu que par le lanceur"),
    },
}
LIBELLES_VOIES = {
    "cli": "lanceur CLI (outils/lancer_mission.py)",
    "sous_session": "sous-session ouverte par la plateforme avec le prompt",
    "prompt": "prompt à copier dans une nouvelle session",
}


class Capacite(NamedTuple):
    nom: str
    etat: str
    note: str = ""
    date: str = ""
    source: str = SOURCE_DETECTION

    def en_dict(self) -> dict:
        return {"etat": self.etat, "source": self.source, "date": self.date, "note": self.note}


Lanceur = Callable[[list[str]], tuple[int, str, str]]


def lancer_local(commande: list[str]) -> tuple[int, str, str]:
    """Seul endroit qui lance un exécutable : `--version` ou `--help`, locaux, avec délai. Lève en cas d'échec."""
    r = subprocess.run(
        commande,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=DELAI_LOCAL_S,
        stdin=subprocess.DEVNULL,
    )
    return r.returncode, r.stdout or "", r.stderr or ""


def _court(texte: str) -> str:
    texte = " ".join(texte.split())
    return texte if len(texte) <= LIMITE_NOTE else texte[:LIMITE_NOTE] + "…"


def _cause(e: BaseException) -> str:
    return type(e).__name__ + (f" ({_court(str(e))})" if str(e) else "")


def _lire(lanceur: Lanceur, commande: list[str]) -> tuple[str | None, str]:
    """(texte, cause) : texte = sortie standard + erreur si le code est 0, sinon None et la cause de l'échec."""
    try:
        code, out, err = lanceur(commande)
    except Exception as e:  # noqa: BLE001 — l'échec devient une cause écrite, jamais « disponible »
        return None, _cause(e)
    texte = (out or "") + ("\n" + err if err and err.strip() else "")
    if code != 0:
        return None, f"code de sortie {code}" + (f" : {_court(texte)}" if texte.strip() else "")
    if not texte.strip():
        return None, "sortie vide"
    return texte, ""


def _est_script_ps1(chemin: str) -> bool:
    return chemin.lower().endswith(".ps1")


def detecter_executable(
    nom: str, executable: str, trouver: Callable[[str], str | None], lanceur: Lanceur, date: str
) -> Capacite:
    """Présence dans le PATH, puis `--version` local. Voir l'en-tête du module pour les états."""
    chemin = trouver(executable)
    if not chemin:
        return Capacite(nom, INDISPONIBLE, f"« {executable} » absent du PATH", date)
    if _est_script_ps1(chemin):
        return Capacite(
            nom,
            NON_TESTE,
            f"« {executable} » est un script .ps1 : il n'est pas lancé ici ; en mode de langage restreint son "
            "enrobage peut renvoyer une erreur (SetShouldExit) et un code de sortie peu fiable ; préfère un "
            "exécutable .exe ou .cmd",
            date,
        )
    options: list[str] = []
    complement = ""
    if nom == "cli_copilot":

        def lire_aide(args: list[str]) -> tuple[int, str]:
            code, out, err = lanceur([chemin, *args])
            return code, (out or "") + ("\n" + err if err and err.strip() else "")

        lue = lire_aide_versionnee(lire_aide)
        analyse = analyser_aide_copilot(lue.texte, lue.avec_option)
        if analyse.versionnee:
            options.append("--no-auto-update")
        complement = _resume_aide(analyse, lue.cause)
    texte, cause = _lire(lanceur, [chemin, "--version", *options])
    if texte is None:
        return Capacite(nom, NON_TESTE, f"« --version » n'a pas pu être lu : {cause}", date)
    version = _court(texte.strip().splitlines()[0])
    note = f"version : {version}" + (f" (lue avec {' '.join(options)})" if options else "")
    if complement:
        note += " ; " + complement
    return Capacite(nom, DISPONIBLE, note, date)


def _resume_aide(aide: AideCopilot, cause: str) -> str:
    if not aide.lue:
        return f"aide non lue ({cause or 'vide'}) : options facultatives et modèle « auto » non détectés"
    return (
        "options de l'aide : "
        + (", ".join(sorted(aide.options)) or "(aucune des options suivies)")
        + " ; --model auto "
        + ("documenté" if aide.modele_auto else "non documenté")
    )


def detecter_python(version: tuple[int, int, int], date: str) -> Capacite:
    texte = ".".join(str(x) for x in version[:3])
    if tuple(version[:2]) < PYTHON_MINI:
        return Capacite(
            "python", INDISPONIBLE, f"Python {texte} : {'.'.join(map(str, PYTHON_MINI))} au moins est requis", date
        )
    return Capacite("python", DISPONIBLE, f"version : {texte}", date)


def inventaire(
    trouver: Callable[[str], str | None],
    lanceur: Lanceur,
    maintenant: dt.datetime,
    version_python: tuple[int, int, int] | None = None,
) -> list[Capacite]:
    """Toutes les capacités détectées, dans l'ordre de `CAPACITES`."""
    date = maintenant.astimezone().strftime("%Y-%m-%d")
    version_python = version_python or sys.version_info[:3]
    out: list[Capacite] = []
    for nom in CAPACITES:
        if nom in EXECUTABLES:
            out.append(detecter_executable(nom, EXECUTABLES[nom], trouver, lanceur, date))
        elif nom == "gh_auth":
            out.append(
                Capacite(nom, NON_TESTE, "vérifier l'authentification contacte le service : jamais fait ici", date)
            )
        elif nom == "python":
            out.append(detecter_python(version_python, date))
        else:
            out.append(Capacite(nom, NON_TESTE, DECLARATIVES[nom], date))
    return out


# ---------- fusion avec config.json ----------
def declaration(texte: str, date: str) -> Capacite:
    """`nom=etat[:note]` vers une capacité déclarée à la main ; lève ValueError si le nom ou l'état est inconnu."""
    nom, _, reste = texte.partition("=")
    etat, _, note = reste.partition(":")
    nom, etat, note = nom.strip(), etat.strip(), note.strip()
    if nom not in CAPACITES:
        raise ValueError(f"capacité « {nom} » inconnue ({', '.join(CAPACITES)}).")
    if etat not in ETATS:
        raise ValueError(f"état « {etat} » inconnu pour {nom} ({', '.join(ETATS)}).")
    return Capacite(nom, etat, note or "déclaré à la main", date, SOURCE_DECLAREE)


def fusionner(existant: object, nouvelles: list[Capacite]) -> tuple[dict, list[str]]:
    """Nouvelle section `capacites` et rapport. Une entrée déclarée à la main n'est pas écrasée par une détection ;
    une déclaration (`source: declaree` dans `nouvelles`) remplace toujours ; les clés inconnues sont gardées."""
    section = dict(existant) if isinstance(existant, dict) else {}
    rapport = []
    for c in nouvelles:
        ancien = section.get(c.nom)
        if c.source == SOURCE_DETECTION and isinstance(ancien, dict) and ancien.get("source") == SOURCE_DECLAREE:
            rapport.append(f"{c.nom} : déclaration conservée ({ancien.get('etat')}), détection ignorée")
            continue
        section[c.nom] = c.en_dict()
    return section, rapport


def lire_section(config: dict) -> list[Capacite]:
    """Capacités déjà écrites dans `config.json` (entrées mal formées ignorées)."""
    out = []
    section = config.get("capacites")
    if not isinstance(section, dict):
        return out
    for nom, v in section.items():
        if isinstance(v, dict) and v.get("etat") in ETATS:
            out.append(Capacite(nom, v["etat"], str(v.get("note", "")), str(v.get("date", "")), v.get("source", "")))
    return out


def ecrire_config(racine: Path, nouvelles: list[Capacite]) -> list[str]:
    """Met à jour la seule clé `capacites` de config.json (écriture atomique). Lève ErreurConfig."""
    config = commun.charger_config(racine)
    if "capacites" in config and not isinstance(config["capacites"], dict):
        raise commun.ErreurConfig("config.json : `capacites` doit être un objet ; rien n'a été écrit.")
    section, rapport = fusionner(config.get("capacites"), nouvelles)
    config["capacites"] = section
    commun.ecrire_json_atomique(Path(racine) / commun.NOM_CONFIG, config)
    return rapport


# ---------- voies de lancement ----------
class Choix(NamedTuple):
    voie: str
    raison: str
    repli: bool  # vrai si ce n'est pas la voie préférée : à faire accepter par l'utilisateur, jamais en silence


def _etat(capacites: dict[str, Capacite], nom: str) -> str:
    c = capacites.get(nom)
    return c.etat if c else NON_TESTE


def voies_possibles(capacites: dict[str, Capacite], moteur: str) -> dict[str, str]:
    """Voie -> pourquoi elle est possible (vide si elle ne l'est pas). Seul `disponible` compte, jamais `non_teste`."""
    possibles = {}
    if _etat(capacites, f"cli_{moteur}") == DISPONIBLE:
        possibles["cli"] = f"`{moteur}` est disponible en ligne de commande"
    if _etat(capacites, "sous_session") == DISPONIBLE:
        possibles["sous_session"] = "la création de sous-session est déclarée disponible"
    possibles["prompt"] = "un texte à copier ne dépend de rien"
    return possibles


def proposer_voie(capacites: dict[str, Capacite], preferee: str | None, moteur: str) -> Choix:
    """Voie proposée : la préférée si elle est possible, sinon la meilleure possible (ordre cli, sous_session,
    prompt) en le disant. C'est une **proposition** : l'utilisateur l'accepte ou non, et après un refus de permission
    ou un échec on s'arrête et on explique, on ne passe jamais seul à une autre voie."""
    possibles = voies_possibles(capacites, moteur)
    if preferee in possibles:
        return Choix(preferee, possibles[preferee], False)
    meilleure = next(v for v in VOIES if v in possibles)
    if preferee in VOIES:
        etat = _etat(capacites, f"cli_{moteur}") if preferee == "cli" else _etat(capacites, "sous_session")
        raison = f"voie préférée « {preferee} » impossible ({etat}) ; repli : {possibles[meilleure]}"
    else:
        raison = possibles[meilleure] + (
            " (aucune préférence valide dans config.json, `voie_preferee`)" if preferee else ""
        )
    return Choix(meilleure, raison, preferee in VOIES)


def controles_non_garantis(voie: str) -> list[str]:
    """Libellés des contrôles que cette voie ne garantit pas (« non » ou « partiel »), avec le détail."""
    return [f"{LIBELLES_CONTROLES[c]} : {GARANTIES[voie][c][1]}" for c in CONTROLES if GARANTIES[voie][c][0] != "oui"]


def tableau_controles(voies: tuple[str, ...] = VOIES) -> str:
    """Tableau Markdown des contrôles par voie (même texte dans `docs/` et dans le récapitulatif)."""
    lignes = ["| Contrôle | " + " | ".join(voies) + " |", "|---|" + "---|" * len(voies)]
    for c in CONTROLES:
        cases = [f"{GARANTIES[v][c][0]} — {GARANTIES[v][c][1]}" for v in voies]
        lignes.append(f"| {LIBELLES_CONTROLES[c]} | " + " | ".join(cases) + " |")
    return "\n".join(lignes)


# ---------- affichage et programme ----------
def tableau(capacites: list[Capacite]) -> str:
    lignes = []
    for c in capacites:
        origine = " (déclarée)" if c.source == SOURCE_DECLAREE else ""
        lignes.append(f"  {c.nom:<18} {c.etat:<12}{origine} {c.date}  {c.note}")
    return "\n".join(lignes)


def main(
    argv: list[str] | None = None,
    *,
    racine: Path = commun.RACINE,
    trouver: Callable[[str], str | None] | None = None,
    lanceur: Lanceur | None = None,
    maintenant: Callable[[], dt.datetime] | None = None,
) -> int:
    import shutil

    ap = argparse.ArgumentParser(
        description="Inventaire des capacités (local, sans service, sans écriture par défaut)."
    )
    ap.add_argument("--ecrire", action="store_true", help="met à jour la section `capacites` de config.json")
    ap.add_argument("--declarer", action="append", default=[], metavar="NOM=ETAT[:NOTE]", help="déclare à la main")
    ap.add_argument("--voie", action="store_true", help="propose la voie de lancement et affiche ses contrôles")
    ap.add_argument("--moteur", choices=("claude", "copilot"), help="moteur visé (défaut : config.json)")
    a = ap.parse_args(argv)

    instant = (maintenant or (lambda: dt.datetime.now(dt.UTC)))()
    date = instant.astimezone().strftime("%Y-%m-%d")
    try:
        declarees = [declaration(d, date) for d in a.declarer]
    except ValueError as e:
        print(f"REFUS : {e}", file=sys.stderr)
        return 2

    detectees = inventaire(trouver or shutil.which, lanceur or lancer_local, instant)
    # une déclaration passée en argument l'emporte sur la détection du même nom
    par_nom = {c.nom: c for c in detectees}
    par_nom.update({c.nom: c for c in declarees})
    nouvelles = [par_nom[n] for n in CAPACITES]

    config: dict = {}
    try:
        config = commun.charger_config(Path(racine))
    except commun.ErreurConfig as e:
        if a.ecrire:
            print(f"REFUS : {e}", file=sys.stderr)
            return 2
        print(f"! {e} (affichage seul)", file=sys.stderr)
    # ce qui s'affiche tient compte des déclarations déjà enregistrées
    existantes = {c.nom: c for c in lire_section(config)}
    effectives = {
        c.nom: existantes[c.nom]
        if c.source == SOURCE_DETECTION and c.nom in existantes and existantes[c.nom].source == SOURCE_DECLAREE
        else c
        for c in nouvelles
    }

    print("Inventaire écrit dans config.json :" if a.ecrire else "Inventaire (dry-run, rien n'est écrit) :")
    print(tableau(list(effectives.values())))
    if a.ecrire:
        try:
            for ligne in ecrire_config(Path(racine), nouvelles):
                print("  ! " + ligne)
        except commun.ErreurConfig as e:
            print(f"REFUS : {e}", file=sys.stderr)
            return 2
    else:
        print("  (ajoute --ecrire pour enregistrer ; les capacités déclarées à la main ne sont jamais écrasées)")

    if a.voie:
        moteur = a.moteur or config.get("moteur_par_defaut") or "claude"
        choix = proposer_voie(effectives, config.get("voie_preferee"), moteur)
        print(f"\nVoie proposée : {choix.voie} — {LIBELLES_VOIES[choix.voie]}")
        print(f"  pourquoi : {choix.raison}" + (" (REPLI : à faire accepter)" if choix.repli else ""))
        print(
            "  À accepter par l'utilisateur ; après un refus de permission ou un échec : s'arrêter, ne pas changer de voie."
        )
        print("\nContrôles garantis par voie :\n" + tableau_controles())
    return 0


if __name__ == "__main__":
    commun.sortie_utf8()
    sys.exit(main())
