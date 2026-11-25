"""Veille : détecte ce qu'on oublie, SANS session d'IA (aucun quota consommé). Lancement à la demande.

Usage (depuis la racine du dépôt) :

    python outils/veille.py [--json] [--sans-ecrire] [--exemples] [--donnees DOSSIER]

Sources lues (toutes en lecture seule) :

- `donnees/veille-taches.json` : les tâches planifiées à surveiller (Windows seulement : `Get-ScheduledTask` et
  `Get-ScheduledTaskInfo`, un seul appel PowerShell sans élévation) ; sur un autre système, cette source est
  ignorée avec un message « non vérifié sur ce système » ;
- `donnees/echeances.json` : les échéances datées ;
- `donnees/missions.jsonl` : le journal des missions ;
- les cartes « En cours » d'Orion (`gh`, via `kanban.lire_cartes`), si `config.json` désigne un tableau.

Une source absente n'est pas une erreur : elle est signalée par une note. Une source illisible est une erreur de
lecture (ligne `!`), les autres sources continuent.

Écrit `donnees/veille.json` (écriture atomique, seul fichier écrit) et affiche un résumé. `--sans-ecrire` n'écrit
rien ; `--json` imprime le rapport complet ; `--exemples` lit les fichiers `*.exemple.json` du dépôt (essai à blanc :
Orion n'est pas lu).

**Les alertes ne créent AUCUNE carte et le programme ne crée AUCUNE tâche planifiée** : `/point` propose la carte,
qui n'est créée qu'après un « ok ». Aucun secret n'est lu ni écrit.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta, tzinfo
from pathlib import Path

import commun
import kanban

DONNEES = commun.RACINE / "donnees"
NOM_SORTIE = "veille.json"

DELAI_POWERSHELL_S = 30
SEUIL_MISSION_MIN = 90  # au-delà (strictement) : mission sans fin (mode 2)
SEUIL_MODE3_H = 72  # session interactive (mode 3) : info au-delà (strictement)
HEURES_REFUS = 24  # fenêtre de recherche des passages refusés (événement 332)
ID_REFUS_SESSION = 332  # Planificateur : tâche non lancée, utilisateur non connecté
JOURNAL_PLANIFICATEUR = "Microsoft-Windows-TaskScheduler/Operational"
JOURS_ATTENTION = 7  # échéance dans 7 jours ou moins : attention
JOURS_INFO = 14  # 14 jours ou moins : info
MAX_EN_COURS = kanban.MAX_EN_COURS  # au-delà (strictement) : info
ANNEE_JAMAIS = 2000  # Windows donne 1999 pour « jamais lancée »

# « en cours » (0x41301), « désactivée » (0x41302), « jamais lancée » (0x41303) : pas des échecs
CODES_NON_ECHEC = frozenset({267009, 267010, 267011})
FINS_MISSION = ("terminee", "echouee", "arretee", "permission_manquante")
NIVEAUX = ("critique", "attention", "info")
_NOM_TACHE = re.compile(r"[A-Za-z0-9_. -]{1,100}")  # refusé sinon : le nom entre dans un script PowerShell

Executeur = Callable[[list], "kanban.Resultat"]
ExecuteurPowerShell = Callable[[str], "tuple[int, str]"]


# ---------- formats ----------
def _duree(minutes: float) -> str:
    minutes = int(minutes)
    if minutes < 90:
        return f"{minutes} min"
    if minutes < 48 * 60:
        return f"{minutes // 60} h {minutes % 60:02d}"
    return f"{minutes // 1440} j"


def _propre(texte: object, limite: int = 200) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", " ", str(texte)).strip()[:limite]


def _alerte(
    cle: str,
    niveau: str,
    source: str,
    titre: str,
    detail: str,
    projet: object = None,
    depuis: str | None = None,
    carte: object = None,
) -> dict:
    return {
        "cle": cle,
        "niveau": niveau,
        "source": source,
        "titre": _propre(titre),
        "detail": _propre(detail, 400),
        "projet": projet if isinstance(projet, str) else None,
        "depuis": depuis,
        "carte_existante": carte if isinstance(carte, str) and carte else None,
    }


def _nombre_positif(valeur: object) -> bool:
    return not isinstance(valeur, bool) and isinstance(valeur, (int, float)) and valeur > 0


# ---------- configuration des tâches ----------
def lire_config_taches(chemin: Path) -> tuple[list[dict], list[str]]:
    """(tâches valides, erreurs). Une entrée invalide est écartée avec une erreur, les autres restent."""
    nom_fichier = Path(chemin).name
    try:
        donnees = json.loads(Path(chemin).read_text(encoding="utf-8"))
    except OSError:
        return [], [f"donnees/{nom_fichier} illisible."]
    except ValueError:
        return [], [f"donnees/{nom_fichier} : JSON invalide."]
    liste = donnees.get("taches") if isinstance(donnees, dict) else None
    if not isinstance(liste, list):
        return [], [f'donnees/{nom_fichier} : {{"taches": [...]}} attendu.']
    taches, erreurs, vus = [], [], set()
    for entree in liste:
        nom = entree.get("nom") if isinstance(entree, dict) else None
        if not isinstance(nom, str) or not _NOM_TACHE.fullmatch(nom):
            erreurs.append(f"{nom_fichier} : nom de tâche refusé ({_propre(nom, 40)!r}).")
            continue
        if nom.lower() in vus:
            erreurs.append(f"{nom_fichier} : tâche en double ({nom}).")
            continue
        if not _nombre_positif(entree.get("periode_min")) or not _nombre_positif(entree.get("retard_facteur")):
            erreurs.append(f"{nom_fichier} : {nom} : periode_min et retard_facteur doivent être > 0.")
            continue
        fenetre = entree.get("fenetre")
        if fenetre is not None and not (
            isinstance(fenetre, list)
            and len(fenetre) == 2
            and all(not isinstance(h, bool) and isinstance(h, (int, float)) and 0 <= h <= 24 for h in fenetre)
            and fenetre[0] != fenetre[1]
        ):
            erreurs.append(f"{nom_fichier} : {nom} : fenêtre invalide, ignorée.")
            fenetre = None
        voulue_off = entree.get("desactivee_volontairement", False)
        if not isinstance(voulue_off, bool):
            erreurs.append(f"{nom_fichier} : {nom} : desactivee_volontairement doit être true/false, ignoré.")
            voulue_off = False
        vus.add(nom.lower())
        taches.append(
            {
                "nom": nom,
                "projet": entree.get("projet"),
                "periode_min": entree["periode_min"],
                "retard_facteur": entree["retard_facteur"],
                "fenetre": fenetre,
                "carte": entree.get("carte"),
                "desactivee_volontairement": voulue_off,
            }
        )
    return taches, erreurs


# ---------- tâches Windows (lecture seule) ----------
def script_powershell(noms: list[str]) -> str:
    """Script d'UNE ligne (pas de guillemets doubles) : lecture seule, dates en secondes Unix."""
    liste = ",".join(f"'{n}'" for n in noms)  # noms validés par `_NOM_TACHE` : pas de `'`
    return (
        "$ErrorActionPreference='SilentlyContinue'; [Console]::OutputEncoding=[Text.Encoding]::UTF8; "
        "$r=@(); "
        f"foreach($n in @({liste})){{ "
        "$t=Get-ScheduledTask -TaskName $n | Select-Object -First 1; "
        "if($null -eq $t){continue}; "
        "$i=Get-ScheduledTaskInfo -TaskName $t.TaskName -TaskPath $t.TaskPath; "
        "$l=$null; if($i.LastRunTime){$l=([DateTimeOffset]$i.LastRunTime).ToUnixTimeSeconds()}; "
        "$x=$null; if($i.NextRunTime){$x=([DateTimeOffset]$i.NextRunTime).ToUnixTimeSeconds()}; "
        "$r+=[pscustomobject]@{Nom=$t.TaskName;State=[string]$t.State;LastRun=$l;"
        "LastResult=$i.LastTaskResult;NextRun=$x} }; "
        "ConvertTo-Json -InputObject $r -Compress"
    )


def executer_powershell(script: str) -> tuple[int, str]:
    """Lance PowerShell (seul endroit qui l'appelle). Remplacé par un faux dans les tests."""
    executable = shutil.which("powershell") or shutil.which("powershell.exe")
    if executable is None:
        raise FileNotFoundError("powershell")
    fini = subprocess.run(
        [executable, "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=DELAI_POWERSHELL_S,
        stdin=subprocess.DEVNULL,
        cwd=tempfile.gettempdir(),
        check=False,
    )
    return fini.returncode, fini.stdout


def _instant(secondes: object) -> datetime | None:
    """Secondes Unix vers datetime UTC ; None si absent, illisible ou « jamais lancée » (avant 2000)."""
    if isinstance(secondes, bool) or not isinstance(secondes, (int, float)):
        return None
    try:
        ts = datetime.fromtimestamp(secondes, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None
    return None if ts.year < ANNEE_JAMAIS else ts


def _code(valeur: object) -> int | None:
    """Code de résultat Windows en entier non signé ; accepte un entier ou une chaîne « 0x… »."""
    if isinstance(valeur, bool):
        return None
    if isinstance(valeur, str):
        try:
            valeur = int(valeur, 0)
        except ValueError:
            return None
    if not isinstance(valeur, (int, float)) or valeur != int(valeur):
        return None
    return int(valeur) & 0xFFFFFFFF


def lire_taches_windows(noms: list[str], executer: ExecuteurPowerShell) -> tuple[dict[str, dict], str | None]:
    """({nom en minuscules: {etat, dernier, resultat, prochain}}, erreur ou None).

    Une tâche absente de la réponse est « introuvable » : c'est à l'appelant d'en tirer l'alerte."""
    try:
        code, sortie = executer(script_powershell(noms))
    except FileNotFoundError:
        return {}, "PowerShell introuvable : tâches Windows non lues."
    except subprocess.TimeoutExpired:
        return {}, f"PowerShell n'a pas répondu en {DELAI_POWERSHELL_S} s : tâches Windows non lues."
    except OSError:
        return {}, "Impossible de lancer PowerShell : tâches Windows non lues."
    if code != 0:
        return {}, f"PowerShell a échoué (code {code}) : tâches Windows non lues."
    try:
        donnees = json.loads((sortie or "").lstrip("﻿").strip() or "[]")
    except ValueError:
        return {}, "Sortie de PowerShell illisible : tâches Windows non lues."
    if isinstance(donnees, dict):
        donnees = [donnees]
    if not isinstance(donnees, list) or not all(isinstance(e, dict) and isinstance(e.get("Nom"), str) for e in donnees):
        return {}, "Sortie de PowerShell inattendue : tâches Windows non lues."
    etats = {}
    for e in donnees:
        etat = e.get("State")
        etats[e["Nom"].lower()] = {
            "etat": etat if isinstance(etat, str) and etat else None,
            "dernier": _instant(e.get("LastRun")),
            "resultat": _code(e.get("LastResult")),
            "prochain": _instant(e.get("NextRun")),
        }
    return etats, None


def script_refus_session(noms: list[str]) -> str:
    """Script d'UNE ligne (pas de guillemets doubles) : lecture seule du journal du Planificateur.

    Événements Id 332 des dernières 24 h dont le message cite une des tâches ; on ne sort JAMAIS le message
    (seulement le nom et l'heure en secondes Unix). Pas de dépendance à la langue du message."""
    liste = ",".join(f"'{n}'" for n in noms)  # noms validés par `_NOM_TACHE` : pas de `'`
    return (
        "$ErrorActionPreference='SilentlyContinue'; [Console]::OutputEncoding=[Text.Encoding]::UTF8; "
        "$r=@(); "
        f"$ev=@(Get-WinEvent -FilterHashtable @{{LogName='{JOURNAL_PLANIFICATEUR}';Id={ID_REFUS_SESSION};"
        f"StartTime=(Get-Date).AddHours(-{HEURES_REFUS})}}); "
        f"foreach($n in @({liste})){{ "
        "$p='(?i)(^|[^A-Za-z0-9_.-])'+[regex]::Escape($n)+'($|[^A-Za-z0-9_.-])'; "
        "foreach($e in $ev){ if([regex]::IsMatch([string]$e.Message,$p)){ "
        "$r+=[pscustomobject]@{Nom=$n;Quand=([DateTimeOffset]$e.TimeCreated).ToUnixTimeSeconds()} } } }; "
        "ConvertTo-Json -InputObject $r -Compress"
    )


def lire_passages_refuses(noms: list[str], executer: ExecuteurPowerShell) -> dict[str, datetime]:
    """{nom en minuscules: heure du dernier passage refusé « session fermée »}.

    Ne lève jamais : toute panne (PowerShell absent, délai, sortie illisible) donne {} et le comportement normal
    reste en place."""
    if not noms:
        return {}
    try:
        code, sortie = executer(script_refus_session(noms))
        if code != 0:
            return {}
        donnees = json.loads((sortie or "").lstrip("﻿").strip() or "[]")
    except (OSError, subprocess.SubprocessError, ValueError):
        return {}
    if isinstance(donnees, dict):
        donnees = [donnees]
    if not isinstance(donnees, list):
        return {}
    connus = {n.lower() for n in noms}
    refus: dict[str, datetime] = {}
    for e in donnees:
        if not isinstance(e, dict) or not isinstance(e.get("Nom"), str):
            continue
        quand, nom = _instant(e.get("Quand")), e["Nom"].lower()
        if quand is not None and nom in connus and (nom not in refus or quand > refus[nom]):
            refus[nom] = quand
    return refus


# ---------- règles 1 à 3 : tâches ----------
def _dans_fenetre(heure: float, fenetre: list) -> bool:
    debut, fin = fenetre
    return debut <= heure < fin if debut < fin else (heure >= debut or heure < fin)


def minutes_en_fenetre(debut: datetime, fin: datetime, fenetre: list) -> float:
    """Minutes de [debut, fin] (heures locales, sans fuseau) tombant dans la fenêtre [h1, h2[ de chaque jour.

    Une fenêtre dont h2 est inférieure ou égale à h1 passe minuit. Un changement d'heure peut fausser d'une heure."""
    h1, h2 = fenetre
    if h2 <= h1:
        h2 += 24
    total, jour = 0.0, debut.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    while jour <= fin:
        a, b = max(debut, jour + timedelta(hours=h1)), min(fin, jour + timedelta(hours=h2))
        if b > a:
            total += (b - a).total_seconds() / 60
        jour += timedelta(days=1)
    return total


def alertes_taches(
    config: list[dict], etats: dict[str, dict], maintenant: datetime, fuseau: tzinfo | None
) -> tuple[list[dict], list[dict]]:
    """(alertes, lignes `taches` de la sortie). `maintenant` est avec fuseau ; `fuseau` : heures locales."""
    local = maintenant.astimezone(fuseau).replace(tzinfo=None)
    alertes, lignes = [], []
    for t in config:
        nom, projet, carte = t["nom"], t["projet"], t["carte"]
        info = etats.get(nom.lower())
        if info is None:
            alertes.append(
                _alerte(
                    f"tache:{nom}:introuvable",
                    "attention",
                    "tache",
                    f"Tâche {nom} introuvable",
                    "Absente du Planificateur de tâches Windows.",
                    projet,
                    None,
                    carte,
                )
            )
            lignes.append(
                {
                    "nom": nom,
                    "etat": "introuvable",
                    "dernier_passage": None,
                    "resultat": None,
                    "prochain_passage": None,
                    "ok": False,
                }
            )
            continue
        dernier, resultat, etat = info["dernier"], info["resultat"], info["etat"]
        depuis = commun.iso(dernier) if dernier else None
        prochain = commun.iso(info["prochain"]) if info["prochain"] else None
        if t.get("desactivee_volontairement") and etat is not None and etat.lower() == "disabled":
            lignes.append(
                {
                    "nom": nom,
                    "etat": etat,
                    "dernier_passage": depuis,
                    "resultat": resultat,
                    "prochain_passage": prochain,
                    "ok": True,  # coupée exprès : aucune alerte (réactivée : règles normales)
                }
            )
            continue
        ok = True
        if resultat is not None and resultat not in CODES_NON_ECHEC and resultat != 0:
            ok = False
            suite = (
                f", dernier passage il y a {_duree((maintenant - dernier).total_seconds() / 60)}." if dernier else "."
            )
            alertes.append(
                _alerte(
                    f"tache:{nom}:echec",
                    "critique",
                    "tache",
                    f"Tâche {nom} en échec",
                    f"Dernier résultat : {resultat} (0x{resultat:X})" + suite,
                    projet,
                    depuis,
                    carte,
                )
            )
        if etat is not None and etat.lower() == "disabled":
            ok = False
            alertes.append(
                _alerte(
                    f"tache:{nom}:desactivee",
                    "attention",
                    "tache",
                    f"Tâche {nom} désactivée",
                    "État Disabled dans le Planificateur de tâches.",
                    projet,
                    depuis,
                    carte,
                )
            )
        else:
            seuil = t["periode_min"] * t["retard_facteur"]
            fenetre = t["fenetre"]
            if fenetre is not None and not _dans_fenetre(local.hour + local.minute / 60, fenetre):
                pass  # hors fenêtre : pas d'alerte
            elif dernier is None:
                ok = False
                alertes.append(
                    _alerte(
                        f"tache:{nom}:silencieuse",
                        "attention",
                        "tache",
                        f"Tâche {nom} silencieuse",
                        "Aucun passage enregistré.",
                        projet,
                        None,
                        carte,
                    )
                )
            else:
                ecoule = (
                    (maintenant - dernier).total_seconds() / 60
                    if fenetre is None
                    else minutes_en_fenetre(dernier.astimezone(fuseau).replace(tzinfo=None), local, fenetre)
                )
                if ecoule > seuil:
                    ok = False
                    alertes.append(
                        _alerte(
                            f"tache:{nom}:silencieuse",
                            "attention",
                            "tache",
                            f"Tâche {nom} silencieuse",
                            f"Pas de passage depuis {_duree(ecoule)}"
                            f"{' (heures de la fenêtre)' if fenetre else ''}, seuil {_duree(seuil)}.",
                            projet,
                            depuis,
                            carte,
                        )
                    )
        lignes.append(
            {
                "nom": nom,
                "etat": etat,
                "dernier_passage": depuis,
                "resultat": resultat,
                "prochain_passage": prochain,
                "ok": ok,
            }
        )
    return alertes, lignes


def noms_silencieuses(alertes: list[dict]) -> list[str]:
    """Noms des tâches pour lesquelles une alerte « silencieuse » a été levée (clé `tache:<nom>:silencieuse`)."""
    debut, fin = "tache:", ":silencieuse"
    return [
        a["cle"][len(debut) : -len(fin)]
        for a in alertes
        if a["source"] == "tache" and a["cle"].startswith(debut) and a["cle"].endswith(fin)
    ]


def adoucir_refus_session(
    alertes: list[dict], etats: dict[str, dict], refus: dict[str, datetime], fuseau: tzinfo | None
) -> list[dict]:
    """Une alerte « silencieuse » dont le dernier passage a été refusé (événement 332, session Windows fermée)
    APRÈS le dernier passage réussi passe d'attention à info. Sans événement : alerte inchangée."""
    sortie = []
    for a in alertes:
        concernees = noms_silencieuses([a])
        quand = refus.get(concernees[0].lower()) if concernees else None
        dernier = (etats.get(concernees[0].lower()) or {}).get("dernier") if concernees else None
        if quand is not None and (dernier is None or quand > dernier):
            heure = quand.astimezone(fuseau).strftime("%H:%M")
            detail = _propre(f"passage refusé : session Windows fermée à {heure}. {a['detail']}", 400)
            a = {**a, "niveau": "info", "detail": detail}
        sortie.append(a)
    return sortie


# ---------- règle 4 : échéances ----------
def lire_echeances(chemin: Path, aujourdhui: date) -> tuple[list[dict], str | None]:
    """(échéances triées par date, `null` à la fin ; message d'erreur ou None).

    Fichier illisible ou JSON invalide : liste vide et erreur. Une date illisible devient `null` et l'entrée porte
    `date_invalide`."""
    try:
        donnees = json.loads(Path(chemin).read_text(encoding="utf-8"))
    except OSError:
        return [], f"Fichier donnees/{Path(chemin).name} illisible."
    except ValueError:
        return [], f"Fichier donnees/{Path(chemin).name} : JSON invalide."
    if not isinstance(donnees, list):
        return [], f"Fichier donnees/{Path(chemin).name} : une liste est attendue."
    resultat = []
    for entree in donnees:
        if not isinstance(entree, dict):
            continue
        jour, invalide = None, False
        if entree.get("date") is not None:
            try:
                jour = date.fromisoformat(str(entree["date"]))
            except ValueError:
                invalide = True
        jours = (jour - aujourdhui).days if jour else None
        item = {
            "date": jour.isoformat() if jour else None,
            "libelle": entree.get("libelle"),
            "projet": entree.get("projet"),
            "carte": entree.get("carte"),
            "jours_restants": jours,
        }
        if invalide:
            item["date_invalide"] = True
        resultat.append(item)
    resultat.sort(key=lambda e: (e["date"] is None, e["date"] or ""))
    return resultat, None


def _slug(texte: object, limite: int = 40) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(texte).lower()).strip("-")[:limite]


def alertes_echeances(echeances: list[dict]) -> tuple[list[dict], list[str]]:
    """Alertes des échéances AVEC date (sortie de `lire_echeances`) + erreurs de dates illisibles."""
    alertes, erreurs = [], []
    for e in echeances:
        if e.get("date_invalide"):
            erreurs.append(f"echeances.json : date illisible ({_propre(e.get('libelle'), 60)}).")
        jours = e.get("jours_restants")
        if e.get("date") is None or jours is None:
            continue
        libelle = e.get("libelle") or "Échéance"
        cle = f"echeance:{e['date']}:{_slug(libelle)}"
        if jours < 0:
            alertes.append(
                _alerte(
                    cle,
                    "critique",
                    "echeance",
                    f"Échéance dépassée : {libelle}",
                    f"Prévue le {e['date']}, dépassée de {-jours} j.",
                    e.get("projet"),
                    f"{e['date']}T00:00:00Z",
                    e.get("carte"),
                )
            )
        elif jours <= JOURS_INFO:
            niveau = "attention" if jours <= JOURS_ATTENTION else "info"
            alertes.append(
                _alerte(
                    cle,
                    niveau,
                    "echeance",
                    f"Échéance proche : {libelle}",
                    f"Le {e['date']}, dans {jours} j.",
                    e.get("projet"),
                    None,
                    e.get("carte"),
                )
            )
    return alertes, erreurs


# ---------- règle 5 : missions sans fin ----------
def alertes_journal(lignes: list[dict], maintenant: datetime) -> list[dict]:
    """Une dernière ligne `lancee` sans fin postérieure depuis plus de 90 min donne une alerte (attention).

    Mode 3 (session interactive) : rien avant 72 h, puis info."""
    lancees: dict[str, tuple[datetime, dict]] = {}
    fins: dict[str, datetime] = {}
    for ligne in lignes:
        mission, ts = ligne.get("mission"), commun.lire_ts(ligne.get("ts"))
        if not isinstance(mission, str) or ts is None:
            continue
        if ligne.get("evenement") == "lancee":
            if mission not in lancees or ts >= lancees[mission][0]:
                lancees[mission] = (ts, ligne)
        elif ligne.get("evenement") in FINS_MISSION:
            if mission not in fins or ts >= fins[mission]:
                fins[mission] = ts
    alertes = []
    for mission, (ts, ligne) in lancees.items():
        if mission in fins and fins[mission] >= ts:
            continue
        minutes = (maintenant - ts).total_seconds() / 60
        if ligne.get("mode") == 3:  # session interactive : pas de ligne de fin attendue
            if minutes > SEUIL_MODE3_H * 60:
                alertes.append(
                    _alerte(
                        f"journal:{mission}",
                        "info",
                        "journal",
                        f"Mission {mission} sans fin",
                        f"session interactive ouverte depuis {_duree(minutes)}, à clôturer au journal.",
                        ligne.get("projet"),
                        commun.iso(ts),
                        None,
                    )
                )
        elif minutes > SEUIL_MISSION_MIN:
            alertes.append(
                _alerte(
                    f"journal:{mission}",
                    "attention",
                    "journal",
                    f"Mission {mission} sans fin",
                    f"Lancée il y a {_duree(minutes)}, aucune ligne terminee / echouee / arretee / permission_manquante.",
                    ligne.get("projet"),
                    commun.iso(ts),
                    None,
                )
            )
    return alertes


# ---------- règle 6 : cartes En cours ----------
def alertes_cartes(cartes: list[dict]) -> list[dict]:
    en_cours = kanban.cartes_en_cours(cartes)
    if len(en_cours) <= MAX_EN_COURS:
        return []
    titres = " ; ".join(_propre(kanban.titre_carte(c), 60) for c in en_cours)
    return [
        _alerte(
            "cartes:en_cours",
            "info",
            "cartes",
            f"{len(en_cours)} cartes « En cours » hors POC",
            f"Maximum {MAX_EN_COURS} : {titres}.",
        )
    ]


def retirer_cartes_faites(alertes: list[dict], cartes: list[dict]) -> list[dict]:
    """Une alerte ne cite pas comme `carte_existante` une carte « Fait » (la panne n'est plus couverte).

    Comparaison par titre ; une carte du même titre pas encore « Fait » garde la citation."""

    def cle(titre: object) -> str:
        return " ".join(str(titre).split()).casefold()

    faits, autres = set(), set()
    for c in cartes:
        if not isinstance(c.get("title"), str):
            continue
        statut = c.get("status")
        (faits if isinstance(statut, str) and statut.strip() == "Fait" else autres).add(cle(c["title"]))
    clos = faits - autres
    return [
        {**a, "carte_existante": None} if a["carte_existante"] and cle(a["carte_existante"]) in clos else a
        for a in alertes
    ]


# ---------- tri, assemblage ----------
def trier(alertes: list[dict]) -> list[dict]:
    """Critique, attention, info ; puis la plus ancienne d'abord (sans date à la fin) ; puis par clé."""
    return sorted(alertes, key=lambda a: (NIVEAUX.index(a["niveau"]), a["depuis"] is None, a["depuis"] or "", a["cle"]))


def analyser(
    donnees: Path,
    maintenant: datetime,
    executer_ps: ExecuteurPowerShell | None = None,
    executer_gh: Executeur | None = None,
    fuseau: tzinfo | None = None,
    *,
    config_kanban: dict | None = None,
    windows: bool | None = None,
    exemples: bool = False,
) -> dict:
    """Rapport complet ; ne lève jamais (chaque source a sa propre erreur). `maintenant` : datetime avec fuseau.

    `windows` : lire les tâches planifiées Windows (défaut : le système est Windows). `exemples` : lit les fichiers
    `*.exemple.json` à la place des vrais et ne lit pas Orion. `config_kanban` : la clé `kanban` de config.json."""
    donnees = Path(donnees)
    windows = sys.platform == "win32" if windows is None else windows
    suffixe = ".exemple.json" if exemples else ".json"
    alertes: list[dict] = []
    erreurs: list[str] = []
    notes: list[str] = []
    lignes_taches: list[dict] = []

    chemin_taches = donnees / f"veille-taches{suffixe}"
    try:  # tâches (règles 1 à 3)
        if not chemin_taches.is_file():
            notes.append(f"donnees/{chemin_taches.name} absent : tâches planifiées non vérifiées.")
        else:
            config, erreurs_config = lire_config_taches(chemin_taches)
            erreurs += erreurs_config
            if config and not windows:
                notes.append("tâches planifiées : non vérifié sur ce système (lecture réservée à Windows).")
            elif config:
                etats, erreur = lire_taches_windows([t["nom"] for t in config], executer_ps or executer_powershell)
                if erreur:
                    erreurs.append(erreur)
                else:
                    alertes_t, lignes_taches = alertes_taches(config, etats, maintenant, fuseau)
                    silencieuses = noms_silencieuses(alertes_t)
                    if silencieuses:  # passage refusé, session fermée
                        refus = lire_passages_refuses(silencieuses, executer_ps or executer_powershell)
                        alertes_t = adoucir_refus_session(alertes_t, etats, refus, fuseau)
                    alertes += alertes_t
    except Exception as exc:  # noqa: BLE001
        erreurs.append(f"Tâches : erreur interne ({type(exc).__name__}).")

    chemin_echeances = donnees / f"echeances{suffixe}"
    try:  # échéances (règle 4)
        if not chemin_echeances.is_file():
            notes.append(f"donnees/{chemin_echeances.name} absent : échéances non vérifiées.")
        else:
            echeances, erreur = lire_echeances(chemin_echeances, maintenant.astimezone(fuseau).date())
            if erreur:
                erreurs.append(erreur)
            alertes_e, erreurs_e = alertes_echeances(echeances)
            alertes += alertes_e
            erreurs += erreurs_e
    except Exception as exc:  # noqa: BLE001
        erreurs.append(f"Échéances : erreur interne ({type(exc).__name__}).")

    chemin_journal = donnees / "missions.jsonl"
    try:  # journal (règle 5)
        if exemples or not chemin_journal.is_file():
            notes.append("donnees/missions.jsonl absent : missions sans fin non vérifiées.")
        else:
            alertes += alertes_journal(commun.lire_journal(chemin_journal), maintenant)
    except Exception as exc:  # noqa: BLE001
        erreurs.append(f"Journal : erreur interne ({type(exc).__name__}).")

    try:  # cartes (règle 6)
        if exemples:
            notes.append("mode exemples : cartes d'Orion non lues.")
        elif not config_kanban or not config_kanban.get("numero"):
            notes.append("Kanban non configuré (config.json) : règle des cartes « En cours » ignorée.")
        else:
            cartes, _ = kanban.lire_cartes(executer_gh or kanban.executer_gh, config_kanban)
            alertes = retirer_cartes_faites(alertes, cartes) + alertes_cartes(cartes)
    except kanban.ErreurGh as exc:
        alertes.append(
            _alerte(
                "cartes:illisibles",
                "info",
                "cartes",
                "Cartes illisibles",
                f"Règle « trop de cartes En cours » ignorée : {exc}",
            )
        )
    except Exception as exc:  # noqa: BLE001
        alertes.append(
            _alerte(
                "cartes:illisibles",
                "info",
                "cartes",
                "Cartes illisibles",
                f"Règle « trop de cartes En cours » ignorée (erreur interne {type(exc).__name__}).",
            )
        )

    return {
        "genere_le": commun.iso(maintenant),
        "alertes": trier(alertes),
        "taches": lignes_taches,
        "erreurs": erreurs,
        "notes": notes,
    }


def resume(rapport: dict) -> list[str]:
    """Lignes du résumé en français : décompte, une ligne par alerte, les erreurs de lecture, puis les notes."""
    n = {niveau: sum(1 for a in rapport["alertes"] if a["niveau"] == niveau) for niveau in NIVEAUX}
    lignes = [f"Veille : {n['critique']} critique, {n['attention']} attention, {n['info']} info."]
    for a in rapport["alertes"]:
        suite = f" (carte existante : {a['carte_existante']})" if a["carte_existante"] else ""
        lignes.append(f"- [{a['niveau']}] {a['titre']} — {a['detail']}{suite}")
    lignes += [f"! {e}" for e in rapport["erreurs"]]
    lignes += [f"~ {n_}" for n_ in rapport.get("notes", [])]
    return lignes


def main(
    argv: list[str] | None = None,
    *,
    donnees: Path | None = None,
    maintenant: Callable[[], datetime] = lambda: datetime.now(UTC),
    executer_ps: ExecuteurPowerShell | None = None,
    executer_gh: Executeur | None = None,
    fuseau: tzinfo | None = None,
    racine: Path = commun.RACINE,
    windows: bool | None = None,
) -> int:
    commun.sortie_utf8()
    parseur = argparse.ArgumentParser(description="Veille : tâches planifiées, échéances, missions, cartes.")
    parseur.add_argument("--json", action="store_true", help="imprime le JSON au lieu du résumé")
    parseur.add_argument("--sans-ecrire", action="store_true", help="n'écrit pas donnees/veille.json")
    parseur.add_argument("--exemples", action="store_true", help="lit les fichiers *.exemple.json (essai à blanc)")
    parseur.add_argument("--donnees", type=Path, help="dossier des données (défaut : donnees/ du dépôt)")
    args = parseur.parse_args(argv)
    dossier = args.donnees or donnees or Path(racine) / "donnees"
    try:
        config_kanban = commun.charger_config(Path(racine)).get("kanban")
    except commun.ErreurConfig:
        config_kanban = None
    rapport = analyser(
        dossier,
        maintenant(),
        executer_ps,
        executer_gh,
        fuseau,
        config_kanban=config_kanban if isinstance(config_kanban, dict) else None,
        windows=windows,
        exemples=args.exemples,
    )
    code = 0
    if not args.sans_ecrire:
        try:
            commun.ecrire_json_atomique(Path(dossier) / NOM_SORTIE, rapport)
        except OSError:
            print("ÉCHEC — impossible d'écrire donnees/veille.json.", file=sys.stderr)
            code = 1
    if args.json:
        print(json.dumps(rapport, ensure_ascii=False, indent=2))
    else:
        print("\n".join(resume(rapport)))
    return code


if __name__ == "__main__":
    sys.exit(main())
