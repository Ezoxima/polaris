---
type: commande
description: Accueil conversationnel : inventaire des capacités, projets, Kanban, moteur, voie de lancement et modèles, une question à la fois
argument-hint: [inventaire | projets | kanban | moteur | voie | modeles]
---

Section demandée : {{arguments}} (vide = toutes les sections, dans l'ordre ci-dessous ; sinon une seule, par son mot
exact). Tu es l'orchestrateur : **tu n'écris pas de code dans les projets**, tu règles Polaris avec moi, en
conversation.

## Règles de la conversation
- **Une seule question à la fois**, avec ta recommandation et sa raison en une phrase. Je réponds, tu passes à la
  suivante. Je peux m'arrêter à tout moment : ce qui est décidé reste décidé.
- **Rien n'est écrit sans mon accord.** Pour chaque fichier (`config.json`, `registre/projets.local.md`,
  `registre/preferences.local.md`, `registre/grille.local.md`), montre le **diff exact** (avant / après), attends mon
  « ok », puis écris. Un `registre/X.local.md` remplace entièrement `registre/X.md` : voir AGENTS.md, « Registres
  locaux » ; pars donc d'une copie du générique, jamais d'un fichier presque vide. Aucun secret, aucun mot de passe,
  aucun jeton dans ces fichiers (leur nom seulement).
- Ce que tu ne sais pas, tu le dis : « non testé » n'est pas « disponible ». N'invente aucune version, aucun nom de
  modèle, aucune option.
- Lis `registre/preferences.md` (ou sa version `.local.md`, voir AGENTS.md) avant de poser la première question.
  Si `config.json` n'existe pas encore, propose de le créer depuis `config.exemple.json` (accord d'abord) et dis
  d'avance ce que tu retires de la copie (les projets fictifs) et ce que tu écriras à la place ; l'exemple ne contient
  ni `moteur_par_defaut` ni `copilot.modeles` : ils viennent de mes réponses, jamais d'une valeur vide.
- **Un seul diff et un seul accord par section** : tu rassembles les changements d'une section en un diff, tu attends
  mon « ok », tu écris. Pas de second accord pour corriger ce que tu viens d'écrire.

## 1. Inventaire (`inventaire`)
Lance `python outils/capacites.py` (il ne fait que chercher les exécutables et lire leur version locale ; il n'écrit
rien) et **montre le tableau tel quel** : disponible, indisponible, non testé, avec la date et la note. Explique en
une phrase chaque ligne qui n'est pas « disponible » et ce qu'elle limite. Puis demande :
- si je veux l'enregistrer (`python outils/capacites.py --ecrire` ; une capacité que j'ai déclarée à la main n'est
  jamais écrasée) ;
- si je veux **déclarer** à la main ce qui ne se détecte pas (`sous_session`, `taches_planifiees`) :
  `python outils/capacites.py --declarer sous_session=disponible:ma note --ecrire`, seulement si je te dis l'avoir
  vu fonctionner.

## 2. Projets (`projets`)
Retire avec moi les projets d'exemple fictifs de `config.json`, puis déclare les miens un par un : nom, dossier de
travail, dépôt git, dossiers en plus, outils autorisés (commandes de test et de lint seulement, jamais de commande
qui écrit à distance). Complète la fiche du projet dans `registre/projets.md` (ou sa version `.local.md`, voir
AGENTS.md) : chemin, statut, mots-clés, règles sensibles. Un projet sans fiche ne sera pas choisi par mots-clés.

## 3. Kanban (`kanban`)
Trois choix, avec la limite de chacun :
- **GitHub Projects (Orion)** : lecture et écriture des cartes par `gh` (installé et connecté). Recommandé si `gh` est
  disponible et que je l'utilise déjà. La création du tableau (`python outils/kanban_init.py`) écrit sur GitHub :
  uniquement si je le demande, après avoir montré ce qu'elle va créer.
- **Un autre outil, en mode manuel** : aucune intégration. Je tiens mes cartes ailleurs, tu me proposes les cartes
  dans la conversation et je les recopie. **Aucune carte n'est créée ni migrée.**
- **Aucun** : pas de cartes ; les missions se décrivent directement dans les briefs.
Note mon choix dans `config.json` (clé `kanban.mode` : `github`, `manuel` ou `aucun`). Dis-moi franchement que les
choix « manuel » et « aucun » limitent `/point`, `/quoi-faire`, `/note` et `/lancer`, qui lisent ou écrivent des cartes.

## 4. Moteur visé (`moteur`)
Demande quel moteur lance mes missions : `claude` ou `copilot` (clé `moteur_par_defaut` de `config.json`). **C'est mon
choix, pas une valeur d'exemple** : sans lui, le lanceur dit « moteur non configuré » et prend `claude` par défaut.
Ta recommandation vient de l'inventaire (quel CLI est « disponible ») et de la plateforme où je te parle (application
Copilot : `copilot` ; Claude Code : `claude`) ; si aucun CLI n'est disponible, dis que le moteur ne règle alors que la
liste d'outils du prompt. Une question, mon accord, le diff, puis l'écriture. `--moteur` l'emporte toujours au lancement.

## 5. Voie de lancement préférée (`voie`)
Relis l'inventaire. Les voies, de la plus contrôlée à la moins contrôlée :
- `cli` : le lanceur (`outils/lancer_mission.py`) ;
- `sous_session` : la plateforme ouvre une session avec un prompt autonome ;
- `prompt` : un texte à copier dans une nouvelle session.
Affiche le tableau des contrôles garantis par voie (`python outils/capacites.py --voie`) et dis clairement qu'une voie
de repli **n'est jamais équivalente au lanceur**. Recommande `cli` si le CLI du moteur est « disponible », sinon la
meilleure voie possible. Note mon choix dans `config.json` (`voie_preferee`). Rappelle que ce choix n'est qu'une
préférence : chaque lancement te redemande mon accord, et après un refus de permission tu t'arrêtes.

## 6. Stratégie de modèle (`modeles`)
- **Claude Code** : rien à régler (`haiku`, `sonnet`, `opus` selon la grille).
- **Copilot** : si l'inventaire dit que `--model auto` est **documenté** par l'aide de mon CLI, propose `auto` pour
  chaque classe (`copilot.modeles.<classe>` = `auto`) en précisant que le modèle réellement utilisé ne sera connu que
  si le fichier d'usage le donne (sinon le journal écrit « non relevé »). Sinon, demande-moi des **noms explicites**
  (commande `/model` dans Copilot). Une valeur vide est refusée par le lanceur : n'en écris jamais, et pars d'un `config.json` sans clé
  `copilot.modeles` (l'exemple n'en contient plus) : tu écris les noms que je valide, rien d'autre. Si je n'utilise pas
  Copilot, n'écris rien.
- Rappelle la règle de la grille : le code s'écrit avec la classe standard ; le modèle fort n'est jamais au-delà de
  l'effort `high` (`registre/grille.md` ou sa version `.local.md`, voir AGENTS.md).

## 7. Fin
Résume en dix lignes ce qui est réglé, ce qui reste « non testé » et ce que je dois essayer moi-même. Si tu as écrit
quelque chose qui change les commandes, lance `python outils/generer_commandes.py` puis `--verifier`. Ne lance aucune
mission, ne crée aucune carte, ne fais aucun `git push`.
