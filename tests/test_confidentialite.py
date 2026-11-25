"""Garde-fou de confidentialité : aucun terme privé, aucun secret, aucun chemin personnel dans les fichiers suivis.

Ce dépôt est une version publique et générique de Polaris. Ce test parcourt tous les fichiers suivis par git (et leurs
noms) et échoue si l'un contient un terme de la liste ci-dessous. Il est volontairement sévère.

Les motifs sont écrits avec UN caractère entre crochets (par exemple `s[o]rare`) : le motif reste équivalent au terme
visé, mais le texte du motif lui-même ne contient jamais le terme. Sans cela, ce fichier ferait échouer la recherche
dans l'historique (`git log -p | grep …`) qu'il est censé faciliter. Un second test vérifie que chaque motif détecte
bien l'exemple reconstitué à l'exécution : une faute de frappe dans un motif ne passe donc pas inaperçue.

Exception unique : l'adresse du dépôt public (propriétaire et nom, dans une URL github.com ou le badge d'intégration
continue) est retirée du texte avant la recherche.
"""

from __future__ import annotations

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


def fichiers_suivis() -> list[Path]:
    """Fichiers suivis par git ; à défaut de dépôt git (archive), tous les fichiers hors `.git`."""
    try:
        sortie = subprocess.run(
            ["git", "-C", str(RACINE), "ls-files", "-z"], capture_output=True, check=True, timeout=60
        ).stdout.decode("utf-8")
        noms = [n for n in sortie.split("\0") if n]
    except (OSError, subprocess.SubprocessError):
        noms = []
    if not noms:
        noms = [
            p.relative_to(RACINE).as_posix()
            for p in RACINE.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(RACINE).parts and "__pycache__" not in p.parts
        ]
    return [RACINE / n for n in noms]


def trouver(texte: str) -> list[str]:
    """Raisons des motifs interdits trouvés dans `texte` (l'adresse du dépôt public est retirée d'abord)."""
    nettoye = ADRESSE_PUBLIQUE.sub("", texte)
    return [raison for motif, raison in COMPILES if motif.search(nettoye)]


def test_il_y_a_des_fichiers_a_verifier():
    assert len(fichiers_suivis()) > 30


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
