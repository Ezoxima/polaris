# Installation

Ce guide installe Polaris sur un poste, pour Claude Code, pour GitHub Copilot, ou pour les deux. Compte une demi-heure.
Poste restreint (pas de CLI d'agent, `gh` non garanti, Python hors du `PATH`, dossier Polaris déjà en place sans Git,
Kanban existant) : suis plutôt [installation-restreinte.md](installation-restreinte.md).
Les outils n'utilisent que la bibliothèque standard de Python : il n'y a rien à installer à l'exécution.

## 1. Prérequis

| Outil | Version | Pourquoi |
|---|---|---|
| Python | 3.11 ou plus | les outils (`outils/*.py`) |
| git | récent | cloner, et les commits locaux des missions |
| GitHub CLI (`gh`) | récent, connecté | le Kanban Orion (`gh auth status`) |
| Claude Code **ou** Copilot CLI | — | les sessions de mission ; voir [copilot.md](copilot.md) pour Copilot |

Le droit `project` de GitHub est nécessaire pour Orion : `gh auth refresh -s project`.
Pour développer ce dépôt lui-même : `pip install -r requirements-dev.txt` (pytest et ruff, versions fixées).

## 2. Cloner et vérifier

```powershell
git clone https://github.com/Ezoxima/polaris.git
cd polaris
python outils/generer_commandes.py --verifier
```

La dernière commande doit répondre `OK : 16 fichiers générés à jour`. Si tu as installé `pytest`, `python -m pytest`
lance les tests (aucun n'appelle `claude`, `copilot` ni `gh`).

Ton instance de Polaris contient ton registre, tes briefs et ta mémoire : garde-la **privée** (un dépôt privé ou un
dossier local). Le `.gitignore` exclut déjà `config.json`, `donnees/` (sauf les exemples), `briefs/`, `memoire/` et
`registre/*.local.md` : mets-y tes versions personnelles des registres plutôt que de modifier les fichiers génériques.

## 3. Configurer

```powershell
Copy-Item config.exemple.json config.json
```

Édite `config.json` :

- `racine_projets` : le dossier qui contient tes projets ;
- `projets` : une entrée par projet, avec `cwd` (le dossier de travail de la mission, relatif à `racine_projets`),
  `git_root` (le dépôt git, sinon `null`), `add_dirs` (dossiers supplémentaires lisibles) et `autorise` (les outils
  que Claude peut utiliser en plus du socle, par exemple `Bash(python -m pytest*)`) ; `autorise_copilot` joue le même
  rôle pour Copilot ;
- `moteur_par_defaut` : `claude` ou `copilot` ;
- `defauts` : budget et durée maximale des missions, nombre de cartes « En cours » (3 par défaut) ;
- `copilot.modeles` : les noms de modèles que ta version de Copilot accepte (voir [copilot.md](copilot.md)).

Ne mets **jamais** de secret dans ce fichier : il ne contient que des chemins et des identifiants de tableau.

## 4. Créer Orion, le Kanban

```powershell
python outils/kanban_init.py --dry-run
python outils/kanban_init.py
```

Le premier appel affiche les commandes `gh` qui seraient lancées, sans rien créer. Le second crée un tableau GitHub
Projects privé « Orion » avec six colonnes (À cadrer, Prêt, En cours, En attente, En pause, Fait) et les champs
Nature, Projet, Taille, Phase, Prochaine étape, `% 5 h` et `% hebdo`, puis écrit ses identifiants dans `config.json`
(clé `kanban`). L'outil refuse s'il existe déjà un tableau de ce titre ou si `config.json` en désigne un ; il ne
supprime et ne modifie jamais rien d'existant. Options : `--proprietaire LOGIN`, `--titre`, `--avec-variante`.

La création du tableau a été essayée sur un vrai compte le 25/11/2026 : tableau créé, six colonnes, sept champs relus
sur GitHub, identifiants écrits dans `config.json`, et refus d'un titre déjà pris. Les tests, eux, simulent `gh`.

Lis le `--dry-run`, puis vérifie le tableau obtenu sur GitHub. Le `--dry-run` n'appelle pas `gh` : il ne détecte donc
pas un titre déjà pris, seul le vrai lancement le fait. Si ton compte a déjà un tableau « Orion », lance
`python outils/kanban_init.py --titre "Mon titre"`. Si la création échoue en route, l'outil dit quel tableau est
incomplet ; supprime-le toi-même, il ne supprime jamais rien.

## 5. Déclarer un premier projet

1. Ajoute sa fiche à `registre/projets.md` (modèle en tête de fichier) : chemin, mots-clés, règles sensibles.
2. Ajoute son entrée à `config.json` (clé `projets`).
3. Dans le dépôt du projet, crée `AGENTS.md` ou `CLAUDE.md` (ses règles propres) et `memoire/INDEX.md`
   (gabarit : `modeles/memoire-axe.md`). Ou laisse `/nouveau-projet` le faire après un entretien de cadrage.

## 6. Lancer une première mission

```powershell
python outils/nouvel_id.py
```

L'identifiant renvoyé (`m-AAAAMMJJ-NN-xxxx`) correspond à un fichier `briefs/<id>.md` vide. Remplis-le avec le gabarit
`modeles/brief.md` (ou laisse `/lancer` l'écrire), puis :

```powershell
python outils/lancer_mission.py <id> --dry-run
python outils/lancer_mission.py <id>
```

Le dry-run montre le dossier de travail, le modèle, l'effort, les outils autorisés et interdits, la durée, le budget et
les contrôles, et refuse proprement si une condition manque. Au lancement, le journal `donnees/missions.jsonl` reçoit
une ligne `lancee`, puis `terminee`, `echouee` ou `arretee`, et le compte rendu est écrit dans
`briefs/<id>-compte-rendu.md`. **Relis toujours le compte rendu et le diff avant de lui faire confiance.**

Pour arrêter toute nouvelle mission : crée un fichier vide `donnees/STOP`.

## 7. Activer la veille

```powershell
Copy-Item donnees/echeances.exemple.json donnees/echeances.json
Copy-Item donnees/veille-taches.exemple.json donnees/veille-taches.json
python outils/veille.py --sans-ecrire
```

Remplace le contenu des deux fichiers par tes échéances et tes tâches planifiées (Windows seulement pour les tâches ;
ailleurs elles sont ignorées avec un message). Pour un essai sur les exemples fictifs :
`python outils/veille.py --exemples --sans-ecrire` (`--exemples` : aucune lecture système, ni Planificateur ni
Orion ; `--sans-ecrire` : aucun fichier écrit ; les deux options sont indépendantes). La veille ne consomme aucun
quota, n'écrit que `donnees/veille.json` (rien avec `--sans-ecrire`, ce que fait `/point`) et ne crée jamais de
carte : `/point` propose, tu valides.

## 8. Personnaliser Polaris

Polaris se règle sans entretien : ses choix par défaut sont ceux de son auteur, regroupés dans des fichiers lisibles.
Garde-les ou modifie une ligne.

| Quoi | Où | Comment |
|---|---|---|
| Dialogue, quota, Kanban, fin de session, Nova | `registre/preferences.md` | Chaque préférence a une valeur par défaut et une ligne « Pour changer » : réécris la ligne. |
| Modèle, effort, durée max selon le type de tâche | `registre/grille.md` | Modifie le tableau ; le lanceur applique le plafond d'effort du modèle fort. |
| Limites mécaniques (cartes « En cours », budgets, durée maximale, moteur) | `config.json`, clés `defauts` et `moteur_par_defaut` | Édite la valeur ; `preferences.md` renvoie à la clé sans la recopier. |
| Projets | `registre/projets.md` et `config.json` (clé `projets`) | Une fiche et une entrée par projet (voir l'étape 5). |
| Commandes (`/point`, `/lancer`…) | `commandes/` | Édite la source, puis `python outils/generer_commandes.py`. Ne modifie jamais `.claude/` ni `.github/skills/`. |
| Colonnes et champs du Kanban | `outils/kanban_init.py` et `registre/kanban.md` | Change la liste dans l'outil avant de créer le tableau ; les recettes `gh` sont dans `kanban.md`. |
| Interdits ajoutés | `registre/preferences.md`, section « Interdits ajoutés » | Écris une ligne par interdit (deux exemples y sont commentés). |

Une seule source de vérité par réglage : si une valeur est dans `config.json`, c'est là qu'on la change.

**Ce qui ne se retire pas.** Le socle des garde-fous (jamais de `git push`, d'argent réel, de mot de passe, de
suppression de données, et le reste de la liste de [garde-fous.md](garde-fous.md)) n'est pas une préférence : le retirer
dans `preferences.md` n'a aucun effet, on n'y **ajoute** que des interdits. Lever un interdit du socle demande de
modifier `AGENTS.md` et `docs/garde-fous.md`, en connaissance de cause et pour une action donnée.

## 9. Utiliser Polaris

**Claude Code** : ouvre une session dans le dossier de Polaris. `CLAUDE.md` charge `AGENTS.md` ; les commandes
`/point`, `/quoi-faire`, `/note`, `/lancer`, `/go`, `/nouveau-projet`, `/conseil` et la skill `creuser` sont disponibles.

**Copilot** : ouvre le dossier de Polaris dans Copilot (CLI ou VS Code). `AGENTS.md` est le noyau ; les commandes sont des
skills (`.github/skills/`). Lis [copilot.md](copilot.md) : plusieurs points y sont marqués « non testé ».

**Modifier une commande** : édite sa source dans `commandes/<nom>.md`, puis `python outils/generer_commandes.py`. Ne
modifie jamais `.claude/` ni `.github/skills/` à la main : l'intégration continue le détecte.

## 10. Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `config.json introuvable` | étape 3 non faite | `Copy-Item config.exemple.json config.json` |
| `projet « x » absent de config.json` | le brief nomme un projet inconnu | l'ajouter à `projets` ou corriger la ligne `Carte : …` |
| `commande « claude » introuvable` | moteur absent du `PATH` | l'installer, ou `--moteur copilot` |
| `Kanban non configuré` | Orion pas créé | étape 4 |
| `gh a échoué (code 1)` | `gh` non connecté ou droit `project` absent | `gh auth login`, puis `gh auth refresh -s project` |
| `une seule mission à la fois par projet` | une mission du même projet est en cours | attendre, ou voir le journal (le blocage tombe après 3 h) |
| `N cartes « En cours »` | plafond du Kanban atteint | terminer une carte, ou `--parallele` si c'est voulu |
| `Failed to start inspector` / `EADDRINUSE` au lancement d'une mission | lancé depuis l'app de bureau Claude Code, le `claude` enfant héritait de `BUN_INSPECT` (débogueur de la session parente) et visait le même port | corrigé en 0.1.2 (le lanceur retire ces variables) ; avec une version antérieure, lancer la mission depuis un terminal ordinaire |
| `Désynchronisé` (CI ou `--verifier`) | un fichier généré a été modifié à la main | `python outils/generer_commandes.py` |
| `REFUS : ces fichiers existent déjà et n'ont pas été générés` | une commande écrite à la main porte le même nom qu'une commande générée | compare et fusionne à la main ; `--forcer` seulement après sauvegarde ([installation-restreinte.md](installation-restreinte.md)) |
| `REFUS : config.json …` (`kanban_init.py`) | `config.json` est invalide ; il n'est jamais remplacé par l'exemple | le corriger, puis relancer |
