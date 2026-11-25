"""Garde-fou de confidentialité : aucun terme privé, aucun secret, aucun chemin personnel dans les fichiers suivis.

Ce dépôt est une version publique et générique de Polaris. Ce test parcourt les fichiers SUIVIS par git
(`git ls-files`, et leurs noms) et échoue si l'un contient un terme de la liste ci-dessous. Il est volontairement
sévère. Il ne lit donc jamais les fichiers de personnalisation locale (`registre/*.local.md`, `donnees/`,
`config.json`, `briefs/`, `memoire/`…) : ils sont ignorés par git et ne seront jamais publiés. Hors dépôt Git (dossier
copié sans `.git`), il parcourt tout le dossier SAUF ce que `.gitignore` écarte, pour la même raison.

Les motifs sont écrits avec UN caractère entre crochets (par exemple `s[o]rare`) : le motif reste équivalent au terme
visé, mais le texte du motif lui-même ne contient jamais le terme. Sans cela, ce fichier ferait échouer la recherche
dans l'historique (`git log -p | grep …`) qu'il est censé faciliter. Un second test vérifie que chaque motif détecte
bien l'exemple reconstitué à l'exécution : une faute de frappe dans un motif ne passe donc pas inaperçue.

Exception unique : l'adresse du dépôt public (propriétaire et nom, dans une URL github.com ou le badge d'intégration
continue) est retirée du texte avant la recherche.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent

# (motif, exemple reconstitué à l'exécution, raison). Tout est insensible à la casse.
MOTIFS = [
    (r"\bs[o]rare", "so" + "rare", "nom d'un service tiers propre à l'auteur"),
    (r"e[z]ox", "ez" + "ox", "pseudonyme de l'auteur (hors adresse du dépôt public)"),
    (r"p[o]kemon", "pok" + "emon", "projet personnel"),
    (r"p[o]kémon", "pok" + "émon", "projet personnel"),
    (r"radical[ _-]?r[e]d", "radical " + "red", "projet personnel"),
    (r"\bn[b]a\b", "n" + "ba", "sport d'un projet personnel"),
    (r"\bm[l]b\b", "m" + "lb", "sport d'un projet personnel"),
    (r"fc_?2[7]", "fc_" + "27", "projet personnel"),
    (r"c[o]hab", "co" + "hab", "projet personnel"),
    (r"taches-ap[p]art", "taches-ap" + "part", "projet personnel"),
    (r"b[o]uygues", "bou" + "ygues", "employeur"),
    (r"\bb[t]bs\b", "b" + "tbs", "employeur"),
    (r"g[c]ochet", "g" + "cochet", "identifiant personnel"),
    (r"g[m]ail", "g" + "mail", "adresse de messagerie personnelle"),
    (r"c:[\\/]+u[s]ers", "c:\\" + "users", "chemin local d'un poste"),
    (r"/home/[a-z][a-z0-9_-]+/", "/ho" + "me/jean/", "chemin local d'un poste"),
    (r"PV[T]_", "PV" + "T_", "identifiant de projet GitHub (Projects v2)"),
    (r"PVT[S]SF_", "PVT" + "SSF_", "identifiant de champ GitHub (Projects v2)"),
    (r"PVT[F]_", "PVT" + "F_", "identifiant de champ GitHub (Projects v2)"),
    (r"gh[p]_", "gh" + "p_", "jeton GitHub"),
    (r"github_p[a]t_", "github_" + "pat_", "jeton GitHub"),
    (r"s[k]-ant", "s" + "k-ant", "clé d'API"),
    (r"ey[J]", "ey" + "J", "début d'un jeton signé"),
    (r"j[w]t", "j" + "wt", "outil propre à un projet personnel"),
    (r"\be[t]h\b", "e" + "th", "monnaie d'un projet personnel"),
    (
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "-".join(["12345678", "1234", "1234", "1234", "123456789abc"]),
        "identifiant de session",
    ),
    (r"[A-Za-z0-9._+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}", "nom" + "@exemple.fr", "adresse de messagerie"),
]
COMPILES = [(re.compile(motif, re.IGNORECASE), raison) for motif, _exemple, raison in MOTIFS]
ADRESSE_PUBLIQUE = re.compile(r"Ezo[x]ima/polaris")


def regles_gitignore(racine: Path) -> list[tuple[bool, str]]:
    """(négation, motif) de `.gitignore` ; un sous-ensemble suffisant : `*`, `?`, dossier final `/`, `!`."""
    try:
        lignes = (racine / ".gitignore").read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    regles = []
    for ligne in (x.strip() for x in lignes):
        if ligne and not ligne.startswith("#"):
            regles.append((ligne.startswith("!"), ligne.lstrip("!").rstrip("/")))
    return regles


def ignore_par_gitignore(relatif: str, regles: list[tuple[bool, str]]) -> bool:
    """Vrai si `.gitignore` écarterait ce chemin (la dernière règle qui correspond l'emporte)."""
    parties = relatif.split("/")
    ignore = False
    for negation, motif in regles:
        if "/" in motif:
            correspond = fnmatch.fnmatch(relatif, motif) or any(
                fnmatch.fnmatch("/".join(parties[:i]), motif) for i in range(1, len(parties))
            )
        else:
            correspond = any(fnmatch.fnmatch(p, motif) for p in parties)
        if correspond:
            ignore = not negation
    return ignore


def fichiers_suivis(racine: Path = RACINE) -> list[Path]:
    """Fichiers suivis par git ; hors dépôt git, tous les fichiers sauf `.git` et ce que `.gitignore` écarte."""
    try:
        sortie = subprocess.run(
            ["git", "-C", str(racine), "ls-files", "-z"], capture_output=True, check=True, timeout=60
        ).stdout.decode("utf-8")
        noms = [n for n in sortie.split("\0") if n]
    except (OSError, subprocess.SubprocessError):
        noms = []
    if not noms:
        regles = regles_gitignore(racine)
        noms = []
        for p in racine.rglob("*"):
            relatif = p.relative_to(racine)
            if p.is_file() and ".git" not in relatif.parts and "__pycache__" not in relatif.parts:
                if not ignore_par_gitignore(relatif.as_posix(), regles):
                    noms.append(relatif.as_posix())
    return [racine / n for n in noms]


def trouver(texte: str) -> list[str]:
    """Raisons des motifs interdits trouvés dans `texte` (l'adresse du dépôt public est retirée d'abord)."""
    nettoye = ADRESSE_PUBLIQUE.sub("", texte)
    return [raison for motif, raison in COMPILES if motif.search(nettoye)]


def test_il_y_a_des_fichiers_a_verifier():
    assert len(fichiers_suivis()) > 30


def test_hors_depot_git_les_fichiers_ignores_ne_sont_pas_parcourus(tmp_path):
    """Un dossier copié sans `.git` : la personnalisation locale (ignorée par git) n'est jamais lue."""
    (tmp_path / ".gitignore").write_text((RACINE / ".gitignore").read_text(encoding="utf-8"), encoding="utf-8")
    publics = ["README.md", "registre/projets.md", "donnees/veille.exemple.json", "outils/x.py"]
    locaux = [
        "registre/preferences.local.md",
        "donnees/missions.jsonl",
        "config.json",
        "briefs/m-1.md",
        "memoire/projet/axe.md",
        "outils/__pycache__/x.pyc",
    ]
    for nom in publics + locaux:
        (tmp_path / nom).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / nom).write_text("contenu", encoding="utf-8")
    vus = {p.relative_to(tmp_path).as_posix() for p in fichiers_suivis(tmp_path)}
    assert vus == {".gitignore", *publics}


def test_chaque_motif_detecte_son_exemple():
    for motif, exemple, _raison in MOTIFS:
        assert re.search(motif, exemple, re.IGNORECASE), f"le motif {motif!r} ne détecte pas son exemple"
    assert not any(exemple in "".join(m for m, _e, _r in MOTIFS) for _m, exemple, _r in MOTIFS[:25])


def test_les_motifs_ne_contiennent_pas_les_termes_qu_ils_visent():
    """Le texte des motifs ne doit pas se déclencher lui-même (sinon la recherche dans l'historique le verrait)."""
    source = Path(__file__).read_text(encoding="utf-8")
    ecrit = "\n".join(ligne for ligne in source.splitlines() if ligne.lstrip().startswith('(r"'))
    assert trouver(ecrit) == []


def test_l_adresse_du_depot_public_est_la_seule_exception():
    depot = "Ezo" + "xima/polaris"
    assert trouver(f"https://github.com/{depot}/actions/workflows/ci.yml/badge.svg") == []
    assert trouver(f"{depot} et " + "Ezo" + "xima ailleurs") == [
        "pseudonyme de l'auteur (hors adresse du dépôt public)"
    ]


@pytest.mark.parametrize("chemin", fichiers_suivis(), ids=lambda p: p.relative_to(RACINE).as_posix())
def test_fichier_sans_terme_interdit(chemin):
    relatif = chemin.relative_to(RACINE).as_posix()
    assert trouver(relatif) == [], f"nom de fichier interdit : {relatif}"
    try:
        texte = chemin.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        pytest.skip("fichier binaire")
    trouves = trouver(texte)
    assert trouves == [], f"{relatif} contient : {', '.join(trouves)}"
