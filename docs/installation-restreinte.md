# Installer sur un poste restreint

Ce guide est distinct de l'[installation par clone neuf](installation.md). Il sert quand le poste limite ce que tu peux
faire : pas de CLI d'agent autorisée, `gh` absent ou non connecté, Python présent mais hors du `PATH`, un dossier
Polaris **déjà en place et sans Git**, un Kanban **déjà utilisé**. Chaque étape dit ce qu'elle lit, ce qu'elle écrit et
l'accord qu'elle demande. Rien n'est installé sans ton accord, et une capacité absente reste absente : on ne la simule
pas et on ne la contourne pas.

Les outils n'ont besoin que de la bibliothèque standard de Python. `pytest` et `ruff` ne servent qu'à développer ce
dépôt.

## 1. Inventaire avant tout

*Lit* : l'état du poste, par des commandes de lecture. *Écrit* : rien. *Accord* : aucun, c'est une lecture ; ne lance
rien qui crée ou modifie.

| Capacité | Comment la constater | Sans elle, ça marche | Différé |
|---|---|---|---|
| CLI `claude` ou `copilot` | `Get-Command claude`, `Get-Command copilot` | commandes conversationnelles dans l'application, registre, modèles, veille en lecture, missions par sous-session lancée à la main (étape 4) | le lanceur automatique `lancer_mission.py` et `/go` |
| `gh` connecté | `Get-Command gh`, puis `gh auth status` | tout sauf Orion | `kanban_init.py`, lecture des cartes (`/point`, `/quoi-faire`, `/lancer`), lecture des cartes « En cours » par la veille |
| Git | `git --version` | tout, sauf les commits locaux des missions | commit automatique du lanceur ; `git init` d'un nouveau projet |
| Python 3.11 ou plus | `py -0p`, ou chemin complet (étape 2) | rien : c'est le prérequis des outils | tous les outils `outils/*.py` |
| Droit de créer des tâches planifiées | à demander à l'administrateur du poste | tout ; la veille *lit* les tâches, elle n'en crée jamais | rien dans Polaris, qui ne crée aucune tâche |

`python outils/capacites.py` fait cet inventaire pour toi, en local et sans écrire (`--ecrire` enregistre le résultat
dans `config.json`) ; la commande `/configurer` le déroule en conversation. Un échec de détection s'y affiche
« non testé » avec sa cause, jamais « disponible ».

Note le résultat. Une ligne « absent » n'est pas un problème à régler : c'est une limite à connaître. N'installe rien
pour la combler sans accord explicite de la personne qui administre le poste.

## 2. Python hors du PATH

*Lit* : la liste des interpréteurs installés. *Écrit* : rien. *Accord* : aucun.

```powershell
py -0p
```

Cette commande liste les interpréteurs connus du lanceur `py` avec leur chemin complet. Si `py` est absent, cherche un
dossier `Python3xx` dans les emplacements d'installation habituels de ton poste. Puis vérifie la version et lance les
outils **avec le chemin complet**, sans modifier le `PATH` :

```powershell
& "C:\chemin\vers\python.exe" --version
& "C:\chemin\vers\python.exe" outils/generer_commandes.py --verifier
```

La version doit être 3.11 ou plus. Il n'y a aucune dépendance à vérifier : un `import` hors bibliothèque standard
dans `outils/` serait un bogue. `pytest` et `ruff` ne servent qu'aux tests de ce dépôt ; ne les installe pas pour
utiliser Polaris.

## 3. Un dossier Polaris déjà en place, sans Git

*Lit* : les deux dossiers (l'existant et la copie de ce dépôt). *Écrit* : une sauvegarde, puis, étape par étape,
seulement ce que tu valides. *Accord* : un accord pour la sauvegarde, puis un accord **par fichier** fusionné.

Quand une instance existe déjà (registre, commandes, journaux qui lui sont propres), ne copie rien par-dessus.

1. **Sauvegarde d'abord.** Copie le dossier existant en entier ailleurs (`Copy-Item -Recurse`), puis vérifie que la
   copie s'ouvre. Ce sera ton retour arrière : restaurer = remettre cette copie à la place.
2. **Dépose ce dépôt à côté**, dans un dossier neuf (clone, ou archive dézippée), jamais dans le dossier existant.
3. **Inventorie les homonymes.** Liste les fichiers qui existent des deux côtés, par catégories :
   - commandes (`.claude/commands/`, `.github/skills/`, `commandes/`) ;
   - registres (`registre/*.md`) et préférences ;
   - modèles (`modeles/`) ;
   - journaux et données (`donnees/`, `briefs/`, `memoire/`).
4. **On n'écrase rien : on compare et on fusionne à la main**, fichier par fichier, en gardant ce qui est à toi. Pour
   les commandes générées, `python outils/generer_commandes.py` **refuse** d'écrire sur un fichier qui n'a pas été
   produit par lui (code 3, liste des fichiers en cause, rien n'est écrit) ; `--forcer` lève ce refus, à n'utiliser
   qu'après sauvegarde et comparaison. `--verifier` signale ces fichiers à part (« non généré par l'outil »).
5. **Pas de `git init` ni de commit imposés.** Un dossier sans Git est un choix valide : les outils marchent sans dépôt
   (seul le commit automatique de fin de mission en a besoin). Si tu veux Git, c'est un acte à part, avec son accord
   (étape 7).

Retour arrière : supprime le dossier modifié et restaure la sauvegarde de l'étape 1.

## 4. Sans CLI d'agent (l'application seulement)

*Lit* : rien de plus. *Écrit* : rien. *Accord* : aucun.

Ce qui fonctionne sans `claude` ni `copilot` : le registre et les préférences (`registre/`), les gabarits
(`modeles/`), les commandes conversationnelles dans l'application, la veille en lecture (`veille.py`), le
générateur de commandes.

**Le mode 2 sans CLI : une sous-session.** Le lanceur `lancer_mission.py` (et donc `/go`) appelle une CLI : il reste
hors de portée. On le remplace par une **sous-session**, une session dédiée dans l'application GitHub Copilot, à qui
l'on donne le prompt autonome écrit par `python outils/lancer_mission.py --prompt <id>` (fichier
`briefs/<id>-prompt.md`, journal `preparee`) : à coller dans une nouvelle session, ou à faire ouvrir par l'application
si elle sait créer des sous-sessions (observé sur une version). Le format du brief, le compte rendu, le journal et les accords
sont les mêmes ; seul le moyen de lancement change (à la main, au lieu du lanceur). C'est l'équivalent du mode 2 sans
CLI, **pas encore éprouvé**. Par rapport au lanceur, il manque :

- le verrou (« une seule mission à la fois par projet ») : n'en ouvre qu'une par projet, à la main ;
- la consommation : tu la relèves et la notes à la main, avant et après ;
- l'écriture automatique du journal `donnees/missions.jsonl` : demande à la sous-session d'écrire sa ligne de fin, ou
  écris-la toi-même, avec ton accord (étape 7).

Si tu utilises quand même le lanceur avec Copilot (CLI disponible), la configuration pas à pas est à l'étape
« 3 bis. Configurer Copilot » de [installation.md](installation.md#3-bis-configurer-copilot). Dans l'application seule,
ce que Copilot charge au démarrage et l'essai pour le vérifier sont dans
[copilot.md](copilot.md#application-seule-sans-cli).

Le tableau complet des contrôles par voie est dans [architecture.md](architecture.md#mode-2-par-paliers). Après un
refus de permission ou un échec, on s'arrête : on ne change pas de voie de soi-même.

Honnêteté : le fonctionnement des commandes de Polaris dans l'application seule n'a **pas été éprouvé** (voir
[copilot.md](copilot.md)). Fais cet essai, dans l'ordre, et note ce qui diffère :

1. ouvre le dossier Polaris dans l'application et demande-lui de lire `AGENTS.md` ;
2. lance `/point` : la commande doit lire le registre et refuser de rien modifier ;
3. lance `/note` avec une idée bidon et vérifie qu'elle **montre** la carte avant de la créer, puis refuse-la ;
4. si une commande n'apparaît pas ou ne lit pas ses fichiers, c'est une limite de l'application : ne la contourne
   pas, note-la.

## 5. Un Kanban déjà en place

*Lit* : ton Kanban existant, comme tu le lis d'habitude. *Écrit* : rien. *Accord* : un seul, sur le choix du système.

**Décide d'abord quel système fait autorité** pour l'état des chantiers : ton Kanban existant ou Orion. Il n'y en a
qu'un.

- Si c'est ton Kanban existant : **ne crée pas un second tableau**, ne lance pas `kanban_init.py`, ne migre et ne
  synchronise rien. Les commandes qui lisent ou écrivent Orion (`/point`, `/quoi-faire`, `/lancer`, `/note`) restent
  limitées ou différées ; un connecteur vers un autre système n'existe pas (voir la feuille de route).
- Si c'est Orion (GitHub Projects) : seulement alors, `python outils/kanban_init.py --dry-run`, puis la création
  (étape 7). L'outil refuse un `config.json` invalide au lieu de le remplacer, et annonce s'il part de l'exemple.

## 6. Veille et journaux

*Lit* : `donnees/`, selon les fichiers présents. *Écrit* : rien avec `--sans-ecrire`. *Accord* : aucun pour la lecture.

```powershell
python outils/veille.py --exemples --sans-ecrire
```

`--exemples` interdit toute lecture du système (Planificateur de tâches, Orion) et ne lit que les fichiers
`*.exemple.json` ; `--sans-ecrire` interdit l'écriture du rapport ; les deux sont indépendants. Sans `--exemples`, la
veille lit tes vraies données, y compris le Planificateur de tâches sous Windows (en lecture seule, un seul appel
PowerShell sans élévation) : lance-la seulement si tu y es autorisé. Un journal `donnees/missions.jsonl` qui
existe déjà et n'a pas ce format est signalé (lignes illisibles comptées, erreur de lecture affichée) ; il n'est
jamais réécrit.

## 7. Accords distincts, un par acte

Un accord général « installe Polaris » ne couvre aucun de ces actes : chacun se demande et se donne séparément.

| Acte | Ce qu'il écrit | Accord à demander |
|---|---|---|
| Créer un dossier de projet | un dossier vide | oui, avec son chemin exact |
| `git init` | un dossier `.git` | oui, séparé ; « sans Git » est valide |
| Premier commit local | un commit (jamais de `git push`) | oui, séparé |
| Créer un tableau Orion | un tableau GitHub Projects, sur ton compte | oui ; seulement si Orion fait autorité (étape 5) |
| Créer une carte | une carte dans le Kanban choisi | oui, après avoir vu son contenu |
| Écrire le journal | une ligne dans `donnees/missions.jsonl` | oui |
| Lancer une mission | une session qui modifie un projet | oui, après récapitulatif |
| Tâche planifiée | une tâche du Planificateur | jamais par Polaris ; c'est à toi, hors de Polaris |

## 8. Confidentialité de ta personnalisation

Ce dépôt est public et générique. Ton registre, tes préférences et tes chemins sont à toi.

- Mets tes versions personnelles dans des fichiers ignorés par Git : `registre/*.local.md` (déjà dans `.gitignore`),
  `donnees/` (sauf les `*.exemple.json`), `config.json`, `briefs/` et `memoire/`.
- Les fichiers de ce dépôt (`registre/projets.md`, `registre/preferences.md`…) restent des modèles génériques : si tu
  les personnalises, fais-le dans ton instance privée, pas dans une copie que tu publierais.
- **Règle des registres locaux** : `registre/X.local.md` **remplace entièrement** `registre/X.md` (on ne lit pas le
  générique). Copie le générique en `.local.md`, puis adapte la copie ; elle ne suit plus les mises à jour du
  générique, à toi de la comparer après une mise à jour de Polaris.
- Le test `tests/test_confidentialite.py` ne regarde que les fichiers **suivis** par Git (ou, sans dépôt Git, ceux
  que `.gitignore` n'écarte pas) : il ne lit pas tes fichiers locaux.
- Ne recopie jamais un secret : on ne cite que son nom.

## 9. Ce que ce guide ne couvre pas

Lanceur automatique sans CLI, connecteur vers un autre Kanban, journaux existants au format différent : voir la feuille de route
du [README](../README.md).
