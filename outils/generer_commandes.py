"""Génère les commandes de Claude Code et de GitHub Copilot depuis la source unique `commandes/`.

Usage (depuis la racine du dépôt) :

    python outils/generer_commandes.py             # écrit les fichiers générés
    python outils/generer_commandes.py --verifier  # n'écrit rien ; code 1 si un fichier est désynchronisé
    python outils/generer_commandes.py --forcer    # écrase aussi un fichier cible qui n'a pas été généré par cet outil

Chaque `commandes/<nom>.md` commence par un en-tête simple entre deux lignes `---` :

    type: commande | skill     (une skill n'est pas une commande : elle se déclenche aussi par son sujet)
    description: une phrase    (obligatoire, 1024 caractères au plus : limite documentée par Copilot)
    argument-hint: ...         (facultatif)
    modele: leger | standard | fort   (facultatif, Claude Code seulement)

Le corps peut contenir :

- `{{arguments}}` : remplacé par `$ARGUMENTS` pour Claude Code, par une périphrase pour Copilot ;
- `<!--claude-->…<!--/claude-->` et `<!--copilot-->…<!--/copilot-->` : bloc conservé pour sa cible seulement.

Sorties :

- Claude Code : `.claude/commands/<nom>.md` (commande) ou `.claude/skills/<nom>/SKILL.md` (skill) ;
- Copilot : `.github/skills/<nom>/SKILL.md` (commande et skill), car les fichiers `.prompt.md` ne fonctionnent
  que dans les sessions locales de VS Code (voir docs/copilot.md).

Les fichiers générés sont versionnés pour qu'un clone fonctionne sans rien lancer ; ils portent un commentaire
« Fichier généré » et ne se modifient jamais à la main.

Garde-fou : un fichier cible qui existe déjà SANS cette marque (une commande écrite à la main, ou venue d'une
autre installation) n'est jamais écrasé. L'écriture est alors refusée en bloc (code 3, aucun fichier écrit,
liste des fichiers en cause), sauf avec `--forcer`. Un fichier qui porte la marque mais dont le contenu a été
modifié à la main est en revanche réécrit : la marque dit qu'il appartient à l'outil. `--verifier` signale les
fichiers sans marque à part (« non généré »).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
MARQUEUR = "Fichier généré par outils/generer_commandes.py"
TYPES = ("commande", "skill")
MODELES_CLAUDE = {"leger": "haiku", "léger": "haiku", "standard": "sonnet", "fort": "opus"}
ARGUMENTS = {"claude": "`$ARGUMENTS`", "copilot": "le texte que j'écris après le nom de la commande"}
CIBLES = ("claude", "copilot")
NOM_VALIDE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LIMITE_NOM = 64
LIMITE_DESCRIPTION = 1024


class ErreurSource(Exception):
    """Une source de `commandes/` est invalide ; le message dit laquelle et pourquoi."""


class ErreurEcrasement(Exception):
    """Des fichiers cibles existent sans la marque de l'outil ; rien n'a été écrit."""

    def __init__(self, fichiers: list[str]):
        super().__init__(", ".join(fichiers))
        self.fichiers = fichiers


@dataclass(frozen=True)
class Commande:
    """Une source analysée."""

    nom: str
    type: str
    description: str
    argument_hint: str | None
    modele: str | None
    corps: str


def lire_source(chemin: Path) -> Commande:
    """Analyse `commandes/<nom>.md` ; lève ErreurSource si l'en-tête est absent ou invalide."""
    nom = chemin.stem
    texte = chemin.read_text(encoding="utf-8").replace("\r\n", "\n")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", texte, re.S)
    if not m:
        raise ErreurSource(f"{chemin.name} : en-tête absent (attendu : `---` autour de `type:` et `description:`).")
    champs: dict[str, str] = {}
    for ligne in m[1].splitlines():
        if not ligne.strip():
            continue
        cle, separateur, valeur = ligne.partition(":")
        if not separateur or not cle.strip():
            raise ErreurSource(f"{chemin.name} : ligne d'en-tête illisible : « {ligne} ».")
        champs[cle.strip()] = valeur.strip()
    inconnus = set(champs) - {"type", "description", "argument-hint", "modele"}
    if inconnus:
        raise ErreurSource(f"{chemin.name} : champ(s) d'en-tête inconnu(s) : {', '.join(sorted(inconnus))}.")
    if not NOM_VALIDE.match(nom) or len(nom) > LIMITE_NOM:
        raise ErreurSource(f"{chemin.name} : nom invalide (minuscules, chiffres, tirets ; {LIMITE_NOM} max).")
    type_ = champs.get("type", "")
    if type_ not in TYPES:
        raise ErreurSource(f"{chemin.name} : `type` doit valoir {' ou '.join(TYPES)}.")
    description = champs.get("description", "")
    if not description:
        raise ErreurSource(f"{chemin.name} : `description` obligatoire.")
    if len(description) > LIMITE_DESCRIPTION:
        raise ErreurSource(f"{chemin.name} : description trop longue ({len(description)} > {LIMITE_DESCRIPTION}).")
    modele = champs.get("modele")
    if modele is not None and modele not in MODELES_CLAUDE:
        raise ErreurSource(f"{chemin.name} : `modele` doit valoir leger, standard ou fort.")
    corps = m[2].lstrip("\n")
    for cible in CIBLES:
        ouvertures = len(re.findall(rf"<!--{cible}-->", corps))
        fermetures = len(re.findall(rf"<!--/{cible}-->", corps))
        if ouvertures != fermetures:
            raise ErreurSource(f"{chemin.name} : balises <!--{cible}--> non appariées.")
    return Commande(nom, type_, description, champs.get("argument-hint"), modele, corps)


def charger_sources(dossier: Path) -> list[Commande]:
    """Toutes les sources, triées par nom. Un dossier vide ou absent est une erreur."""
    fichiers = sorted(dossier.glob("*.md")) if dossier.is_dir() else []
    if not fichiers:
        raise ErreurSource(f"aucune source dans {dossier}.")
    return [lire_source(f) for f in fichiers]


def adapter_corps(corps: str, cible: str) -> str:
    """Garde les blocs de la cible, retire ceux de l'autre, remplace `{{arguments}}`."""
    for autre in (c for c in CIBLES if c != cible):
        corps = re.sub(rf"<!--{autre}-->.*?<!--/{autre}-->\n?", "", corps, flags=re.S)
    corps = re.sub(rf"<!--/?{cible}-->\n?", "", corps)
    return corps.replace("{{arguments}}", ARGUMENTS[cible])


def _entete(champs: list[tuple[str, str]]) -> str:
    """En-tête YAML ; les valeurs sont écrites entre guillemets (JSON est du YAML valide)."""
    lignes = [f"{cle}: {json.dumps(valeur, ensure_ascii=False)}" for cle, valeur in champs]
    return "---\n" + "\n".join(lignes) + "\n---\n"


def rendre(cmd: Commande, cible: str) -> tuple[str, str]:
    """(chemin relatif, contenu) du fichier généré pour cette cible."""
    corps = adapter_corps(cmd.corps, cible)
    note = f"<!-- {MARQUEUR} à partir de commandes/{cmd.nom}.md : ne pas modifier à la main. -->\n\n"
    if cible == "claude" and cmd.type == "commande":
        champs = [("description", cmd.description)]
        if cmd.argument_hint:
            champs.append(("argument-hint", cmd.argument_hint))
        if cmd.modele:
            champs.append(("model", MODELES_CLAUDE[cmd.modele]))
        chemin = f".claude/commands/{cmd.nom}.md"
    else:
        champs = [("name", cmd.nom), ("description", cmd.description)]
        if cmd.argument_hint and cible == "copilot":
            champs.append(("argument-hint", cmd.argument_hint))
        base = ".claude/skills" if cible == "claude" else ".github/skills"
        chemin = f"{base}/{cmd.nom}/SKILL.md"
    return chemin, _entete(champs) + note + corps


def attendus(commandes: list[Commande]) -> dict[str, str]:
    """Tous les fichiers à produire : chemin relatif (avec `/`) → contenu."""
    sortie: dict[str, str] = {}
    for cmd in commandes:
        for cible in CIBLES:
            chemin, contenu = rendre(cmd, cible)
            sortie[chemin] = contenu
    return sortie


def orphelins(racine: Path, attendus_: dict[str, str]) -> list[str]:
    """Fichiers générés (porteurs du marqueur) dont la source a disparu."""
    candidats = [
        *racine.glob(".claude/commands/*.md"),
        *racine.glob(".claude/skills/*/SKILL.md"),
        *racine.glob(".github/skills/*/SKILL.md"),
    ]
    trouves = []
    for f in candidats:
        rel = f.relative_to(racine).as_posix()
        if rel in attendus_:
            continue
        if MARQUEUR in f.read_text(encoding="utf-8", errors="replace"):
            trouves.append(rel)
    return sorted(trouves)


def _normaliser(texte: str) -> str:
    return texte.replace("\r\n", "\n")


def _est_genere(fichier: Path) -> bool:
    """Vrai si le fichier porte la marque de l'outil (donc qu'il a le droit de le réécrire)."""
    return MARQUEUR in fichier.read_text(encoding="utf-8", errors="replace")


def non_generes(racine: Path, attendus_: dict[str, str]) -> list[str]:
    """Cibles qui existent déjà sans la marque de l'outil : elles ne sont pas à lui."""
    return sorted(rel for rel in attendus_ if (racine / rel).is_file() and not _est_genere(racine / rel))


def verifier(racine: Path, attendus_: dict[str, str]) -> list[str]:
    """Problèmes de synchronisation (liste vide si tout est à jour)."""
    problemes = []
    for rel, contenu in sorted(attendus_.items()):
        f = racine / rel
        if not f.is_file():
            problemes.append(f"manquant : {rel}")
        elif not _est_genere(f):
            problemes.append(f"non généré par l'outil (écrit à la main ?) : {rel}")
        elif _normaliser(f.read_text(encoding="utf-8")) != contenu:
            problemes.append(f"désynchronisé : {rel}")
    problemes += [f"orphelin (source supprimée) : {rel}" for rel in orphelins(racine, attendus_)]
    return problemes


def ecrire(racine: Path, attendus_: dict[str, str], *, forcer: bool = False) -> list[str]:
    """Écrit les fichiers qui diffèrent ; renvoie ceux qui ont changé.

    Sans `forcer`, lève ErreurEcrasement avant d'écrire quoi que ce soit si une cible existe sans la marque.
    """
    if not forcer and (etrangers := non_generes(racine, attendus_)):
        raise ErreurEcrasement(etrangers)
    modifies = []
    for rel, contenu in sorted(attendus_.items()):
        f = racine / rel
        if f.is_file() and _normaliser(f.read_text(encoding="utf-8")) == contenu:
            continue
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(contenu, encoding="utf-8", newline="\n")
        modifies.append(rel)
    return modifies


def main(argv: list[str] | None = None, *, racine: Path = RACINE) -> int:
    ap = argparse.ArgumentParser(description="Génère les commandes Claude Code et Copilot depuis commandes/.")
    ap.add_argument("--verifier", action="store_true", help="n'écrit rien ; code 1 si un fichier est désynchronisé")
    ap.add_argument(
        "--forcer",
        action="store_true",
        help="écrase aussi les fichiers cibles qui n'ont pas été générés par cet outil (sinon refus, code 3)",
    )
    a = ap.parse_args(argv)
    try:
        attendus_ = attendus(charger_sources(racine / "commandes"))
    except ErreurSource as e:
        print(f"ERREUR : {e}", file=sys.stderr)
        return 2
    if a.verifier:
        problemes = verifier(racine, attendus_)
        for p in problemes:
            print(p, file=sys.stderr)
        if problemes:
            print("Désynchronisé : lance `python outils/generer_commandes.py` puis relis le diff.", file=sys.stderr)
            return 1
        print(f"OK : {len(attendus_)} fichiers générés à jour.")
        return 0
    try:
        modifies = ecrire(racine, attendus_, forcer=a.forcer)
    except ErreurEcrasement as e:
        print(
            "REFUS : ces fichiers existent déjà et n'ont pas été générés par cet outil ; rien n'a été écrit :",
            file=sys.stderr,
        )
        for rel in e.fichiers:
            print(f"  {rel}", file=sys.stderr)
        print(
            "Compare-les à la main avec ce que l'outil produirait, fusionne ce qui doit l'être, "
            "ou relance avec --forcer pour les écraser (sauvegarde d'abord).",
            file=sys.stderr,
        )
        return 3
    for rel in modifies:
        print(f"écrit : {rel}")
    for rel in orphelins(racine, attendus_):
        print(f"! orphelin (source supprimée, à retirer à la main) : {rel}", file=sys.stderr)
    print(f"{len(modifies)} fichier(s) écrit(s), {len(attendus_) - len(modifies)} déjà à jour.")
    return 0


if __name__ == "__main__":
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    sys.exit(main())
