"""Réserve un identifiant de mission unique : m-AAAAMMJJ-NN-xxxx (xxxx = 4 caractères hexadécimaux aléatoires).

Usage (depuis la racine du dépôt) :

    python outils/nouvel_id.py [--nb 3]

Crée `briefs/<id>.md` (vide) en création exclusive, puis affiche l'identifiant : deux sessions simultanées ne
peuvent plus écrire dans le même fichier de brief. `NN` est un compteur du jour (lisible) ; le suffixe aléatoire
garantit l'unicité.
"""

from __future__ import annotations

import argparse
import re
import secrets
import sys
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
NUM = re.compile(r"^m-(\d{8})-(\d{2,})")


def reserver(racine: Path = RACINE, jour: date | None = None) -> str:
    """Réserve et renvoie un nouvel identifiant ; le fichier de brief vide est créé dans `briefs/`."""
    briefs = Path(racine) / "briefs"
    briefs.mkdir(exist_ok=True)
    d = (jour or date.today()).strftime("%Y%m%d")
    nn = 1 + max(
        (int(m.group(2)) for p in briefs.rglob("m-*.md") if (m := NUM.match(p.name)) and m.group(1) == d),
        default=0,
    )
    for _ in range(50):
        ident = f"m-{d}-{nn:02d}-{secrets.token_hex(2)}"
        try:
            with open(briefs / f"{ident}.md", "x", encoding="utf-8"):
                return ident
        except FileExistsError:
            continue
    raise RuntimeError("impossible de réserver un identifiant (50 tentatives).")


def main(argv: list[str] | None = None, *, racine: Path = RACINE) -> int:
    ap = argparse.ArgumentParser(description="Réserve un ou plusieurs identifiants de mission.")
    ap.add_argument("--nb", type=int, default=1, help="nombre d'identifiants à réserver (défaut : 1)")
    a = ap.parse_args(argv)
    if a.nb < 1:
        print("ERREUR : --nb doit être au moins 1.", file=sys.stderr)
        return 2
    for _ in range(a.nb):
        print(reserver(racine))
    return 0


if __name__ == "__main__":
    sys.exit(main())
