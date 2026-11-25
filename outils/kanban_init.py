"""Crée Orion, le tableau GitHub Projects de Polaris, avec ses six colonnes et ses champs.

Usage (depuis la racine du dépôt) :

    python outils/kanban_init.py --dry-run                    # affiche ce qui serait créé, ne crée rien
    python outils/kanban_init.py [--proprietaire LOGIN] [--titre Orion] [--avec-variante]

Ce que l'outil fait :

1. refuse si `config.json` contient déjà un tableau (`kanban.numero` ou `kanban.projet_id`) ;
2. refuse si un tableau du même titre existe déjà chez ce propriétaire ;
3. crée le tableau (`gh project create`, privé par défaut) ;
4. remplace les options du champ `Status` par les six colonnes : À cadrer, Prêt, En cours, En attente, En pause, Fait ;
5. crée les champs Nature, Projet, Taille, Phase, Prochaine étape, % 5 h, % hebdo (et Variante avec `--avec-variante`) ;
6. relit les identifiants et les range dans `config.json`, clé `kanban`.

Ce que l'outil ne fait jamais : supprimer ou modifier un tableau, une carte ou un champ existant. Si la création
échoue en cours de route, il dit quel tableau est incomplet ; c'est à toi de le supprimer ou de le compléter.

Prérequis : `gh` installé et connecté, avec le droit `project` (`gh auth refresh -s project`).
`gh` est appelé par `kanban.executer_gh`, remplacé par un faux dans les tests : aucun test n'écrit sur GitHub.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

import commun
import kanban

COULEURS = ("GRAY", "BLUE", "YELLOW", "ORANGE", "PURPLE", "GREEN")  # une par colonne, dans l'ordre
TITRE_PAR_DEFAUT = "Orion"
PROPRIETAIRE_PAR_DEFAUT = "@me"


@dataclass(frozen=True)
class Champ:
    """Un champ à créer : son nom, son type GitHub et, pour un choix unique, ses options."""

    nom: str
    type: str  # TEXT | NUMBER | SINGLE_SELECT
    options: tuple[str, ...] = ()


class Refus(Exception):
    """Refus volontaire (code 2) : rien n'a été créé."""


class ErreurPartielle(Exception):
    """Le tableau a été créé mais l'initialisation n'est pas allée au bout (code 1)."""


def champs_a_creer(avec_variante: bool = False) -> list[Champ]:
    """Les champs de l'original, dans l'ordre de création."""
    champs = [
        Champ("Nature", "SINGLE_SELECT", kanban.NATURES),
        Champ("Projet", "TEXT"),
        Champ("Taille", "SINGLE_SELECT", kanban.TAILLES),
        Champ("Phase", "SINGLE_SELECT", kanban.PHASES),
        Champ("Prochaine étape", "TEXT"),
        Champ("% 5 h", "NUMBER"),
        Champ("% hebdo", "NUMBER"),
    ]
    if avec_variante:
        champs.append(Champ("Variante", "TEXT"))
    return champs


def _proprietaire_args(proprietaire: str, *, pour_liste: bool = False) -> list[str]:
    """`gh project list` sans `--owner` désigne l'utilisateur connecté ; les autres commandes acceptent `@me`."""
    if pour_liste and proprietaire == PROPRIETAIRE_PAR_DEFAUT:
        return []
    return ["--owner", proprietaire]


def commande_liste(proprietaire: str) -> list[str]:
    return ["project", "list", *_proprietaire_args(proprietaire, pour_liste=True), "--format", "json", "--limit", "100"]


def commande_creation(proprietaire: str, titre: str) -> list[str]:
    return ["project", "create", *_proprietaire_args(proprietaire), "--title", titre, "--format", "json"]


def commande_champs(numero: int | str, proprietaire: str) -> list[str]:
    return ["project", "field-list", str(numero), *_proprietaire_args(proprietaire), "--format", "json"]


def mutation_status(id_champ: str) -> str:
    """Mutation GraphQL qui remplace les options du champ `Status` par les six colonnes.

    Les noms viennent de constantes du dépôt (jamais d'une saisie) : pas d'injection possible. Sur un tableau
    neuf, aucune carte n'existe encore : le remplacement des options n'efface aucune valeur."""
    options = ",".join(
        f'{{name:"{nom}",color:{COULEURS[i % len(COULEURS)]},description:""}}' for i, nom in enumerate(kanban.COLONNES)
    )
    return (
        f'mutation{{updateProjectV2Field(input:{{fieldId:"{id_champ}",singleSelectOptions:[{options}]}})'
        "{projectV2Field{... on ProjectV2SingleSelectField{id options{id name}}}}}"
    )


def commande_status(id_champ: str) -> list[str]:
    return ["api", "graphql", "-f", f"query={mutation_status(id_champ)}"]


def commande_champ(numero: int | str, proprietaire: str, champ: Champ) -> list[str]:
    args = [
        "project",
        "field-create",
        str(numero),
        *_proprietaire_args(proprietaire),
        "--name",
        champ.nom,
        "--data-type",
        champ.type,
    ]
    if champ.options:
        args += ["--single-select-options", ",".join(champ.options)]
    return args + ["--format", "json"]


def plan_dry_run(proprietaire: str, titre: str, avec_variante: bool) -> list[str]:
    """Lignes affichées par `--dry-run` : les commandes `gh` dans l'ordre, sans en lancer aucune."""
    etapes = [
        (commande_liste(proprietaire), "lecture : refus si un tableau de ce titre existe déjà"),
        (commande_creation(proprietaire, titre), "crée le tableau"),
        (commande_champs("<numero>", proprietaire), "lecture : identifiant du champ Status"),
        (commande_status("<id du champ Status>"), "remplace les options de Status par les six colonnes"),
    ]
    for champ in champs_a_creer(avec_variante):
        etapes.append((commande_champ("<numero>", proprietaire, champ), f"crée le champ {champ.nom} ({champ.type})"))
    etapes.append((commande_champs("<numero>", proprietaire), "relecture : identifiants des champs et des options"))
    lignes = []
    for i, (args, role) in enumerate(etapes, start=1):
        affichage = "gh " + shlex.join(args)
        if len(affichage) > 150:
            affichage = affichage[:147] + "..."
        lignes.append(f"  {i:>2}. {affichage}")
        lignes.append(f"      → {role}")
    return lignes


def _chercher(champs: list[dict], nom: str) -> dict:
    for c in champs:
        if isinstance(c, dict) and c.get("name") == nom:
            return c
    raise kanban.ErreurGh(f"champ « {nom} » introuvable dans le tableau créé.")


def _champs_du_tableau(executer: kanban.Executeur, numero: int, proprietaire: str) -> list[dict]:
    donnees = kanban.lire_json(executer, commande_champs(numero, proprietaire))
    champs = donnees.get("fields") if isinstance(donnees, dict) else None
    if not isinstance(champs, list):
        raise kanban.ErreurGh("Sortie de `gh project field-list` inattendue.")
    return champs


def table_des_champs(champs: list[dict], noms: list[str]) -> dict[str, dict]:
    """{nom du champ: {id, options: {nom de l'option: id}}} pour les champs demandés."""
    table = {}
    for nom in noms:
        champ = _chercher(champs, nom)
        options = {o["name"]: o["id"] for o in champ.get("options", []) if isinstance(o, dict) and "id" in o}
        table[nom] = {"id": champ.get("id"), "options": options}
    return table


def verifier_config_vierge(config: dict) -> None:
    """Refuse si `config.json` désigne déjà un tableau."""
    k = config.get("kanban")
    if isinstance(k, dict) and (k.get("numero") or k.get("projet_id")):
        raise Refus(
            f"config.json contient déjà un tableau (numéro {k.get('numero')}) : rien n'est créé. "
            "Pour en créer un autre, vide d'abord `kanban.numero` et `kanban.projet_id` à la main."
        )


def initialiser(executer: kanban.Executeur, config: dict, proprietaire: str, titre: str, avec_variante: bool) -> dict:
    """Crée le tableau et renvoie la clé `kanban` à écrire dans config.json. Lève Refus ou ErreurPartielle."""
    verifier_config_vierge(config)
    try:
        existants = kanban.lire_json(executer, commande_liste(proprietaire))
    except kanban.ErreurGh as e:
        raise Refus(f"impossible de vérifier les tableaux existants : {e}") from None
    projets = existants.get("projects", []) if isinstance(existants, dict) else []
    for p in projets:
        if isinstance(p, dict) and p.get("title") == titre:
            raise Refus(
                f"un tableau « {titre} » existe déjà (numéro {p.get('number')}) : rien n'est créé. "
                "Renseigne-le à la main dans config.json ou choisis un autre `--titre`."
            )
    try:
        cree = kanban.lire_json(executer, commande_creation(proprietaire, titre))
        numero, projet_id = int(cree["number"]), str(cree["id"])
    except (kanban.ErreurGh, KeyError, TypeError, ValueError) as e:
        raise Refus(f"création du tableau impossible : {e}") from None
    try:
        champs = _champs_du_tableau(executer, numero, proprietaire)
        id_status = str(_chercher(champs, "Status")["id"])
        reponse = kanban.appeler(executer, commande_status(id_status))
        if reponse.code != 0:
            raise kanban.ErreurGh(
                f"mise à jour du champ Status refusée (code {reponse.code}) : {reponse.erreur.strip()[:200]}"
            )
        for champ in champs_a_creer(avec_variante):
            reponse = kanban.appeler(executer, commande_champ(numero, proprietaire, champ))
            if reponse.code != 0:
                raise kanban.ErreurGh(
                    f"création du champ {champ.nom} refusée (code {reponse.code}) : {reponse.erreur.strip()[:200]}"
                )
        champs = _champs_du_tableau(executer, numero, proprietaire)
        noms = ["Status"] + [c.nom for c in champs_a_creer(avec_variante)]
        table = table_des_champs(champs, noms)
    except kanban.ErreurGh as e:
        raise ErreurPartielle(
            f"le tableau n°{numero} a été créé mais n'est pas complet : {e} "
            "Supprime-le ou complète-le toi-même sur GitHub ; l'outil ne supprime jamais rien."
        ) from None
    return {
        "proprietaire": proprietaire,
        "titre": titre,
        "numero": numero,
        "projet_id": projet_id,
        "champs": table,
    }


def ecrire_config(racine: Path, config: dict, section_kanban: dict) -> Path:
    """Range la clé `kanban` dans config.json (créé depuis l'exemple s'il n'existe pas)."""
    config = dict(config)
    config["kanban"] = section_kanban
    chemin = Path(racine) / commun.NOM_CONFIG
    commun.ecrire_json_atomique(chemin, config)
    return chemin


def _config_ou_exemple(racine: Path) -> dict:
    """config.json s'il existe, sinon le contenu de config.exemple.json, sinon un objet vide."""
    try:
        return commun.charger_config(racine)
    except commun.ErreurConfig:
        pass
    try:
        return json.loads((Path(racine) / commun.NOM_CONFIG_EXEMPLE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def main(
    argv: list[str] | None = None, *, racine: Path = commun.RACINE, executer: kanban.Executeur | None = None
) -> int:
    ap = argparse.ArgumentParser(description="Crée le tableau Orion (GitHub Projects) et range ses identifiants.")
    ap.add_argument("--dry-run", action="store_true", help="affiche ce qui serait créé, ne crée rien")
    ap.add_argument("--proprietaire", help="login GitHub du propriétaire (défaut : config.json, sinon @me)")
    ap.add_argument("--titre", default=TITRE_PAR_DEFAUT, help=f"titre du tableau (défaut : {TITRE_PAR_DEFAUT})")
    ap.add_argument("--avec-variante", action="store_true", help="ajoute le champ texte facultatif « Variante »")
    a = ap.parse_args(argv)

    config = _config_ou_exemple(racine)
    existant = config.get("kanban") if isinstance(config.get("kanban"), dict) else {}
    proprietaire = a.proprietaire or existant.get("proprietaire") or PROPRIETAIRE_PAR_DEFAUT

    try:
        verifier_config_vierge(config)
    except Refus as r:
        print(f"REFUS : {r}", file=sys.stderr)
        return 2

    if a.dry_run:
        print(f"[dry-run] Orion : création du tableau GitHub Projects « {a.titre} » (propriétaire : {proprietaire}).")
        print("Rien n'est créé et `gh` n'est pas appelé. Commandes qui seraient lancées, dans l'ordre :")
        print("\n".join(plan_dry_run(proprietaire, a.titre, a.avec_variante)))
        print("Colonnes (champ Status) : " + " · ".join(kanban.COLONNES))
        print("Champs : " + " · ".join(c.nom for c in champs_a_creer(a.avec_variante)))
        print(f"Ensuite : écrit la clé `kanban` (numéro, id du projet, id des champs) dans {commun.NOM_CONFIG}.")
        return 0

    try:
        section = initialiser(executer or kanban.executer_gh, config, proprietaire, a.titre, a.avec_variante)
    except Refus as r:
        print(f"REFUS : {r}", file=sys.stderr)
        return 2
    except ErreurPartielle as e:
        print(f"ÉCHEC : {e}", file=sys.stderr)
        return 1
    chemin = ecrire_config(racine, config, section)
    print(f"Tableau « {a.titre} » créé (numéro {section['numero']}). Identifiants écrits dans {chemin.name}.")
    print("Colonnes : " + " · ".join(kanban.COLONNES))
    return 0


if __name__ == "__main__":
    commun.sortie_utf8()
    sys.exit(main())
