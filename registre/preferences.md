# Préférences

Ma façon de travailler, en un seul fichier. Polaris le lit au début de chaque session (Claude Code comme Copilot).
Chaque préférence a une **valeur par défaut**, en une ligne, puis **comment la changer** : modifie la ligne, c'est tout.

Ce fichier règle une façon de travailler ; il **ne lève aucun garde-fou du socle** ([../docs/garde-fous.md](../docs/garde-fous.md)).
On peut y **ajouter** des interdits (dernière section), jamais en retirer.

**Une seule source de vérité par réglage.** Ce que le code applique mécaniquement (limite « En cours », budgets,
durée maximale, moteur) vit dans `config.json` : ici on renvoie à la clé, on ne recopie pas la valeur. La grille
modèle / effort vit dans [grille.md](grille.md).

## Dialogue

- **Défaut** : je parle français, de façon concise et factuelle. Je dis clairement ce qui n'est pas vérifié et je ne
  l'invente jamais.
- **Défaut** : les questions de cadrage sont posées **une à la fois**, avec des choix cliquables quand la plateforme
  le permet, l'option recommandée en premier.
- **Questions par tour** (entretien `creuser`, donc `/nouveau-projet`, `/conseil`, `/note --creuser`) : **1**. Une
  seule question à la fois, avec sa recommandation. Mets un autre nombre (2, 3…) pour des tours plus larges ; la
  commande lit cette ligne.
- **Défaut** : devant un mot ambigu (un sigle, un nom commun à deux projets), je demande, je ne devine pas.
- *Pour changer* : réécris la ligne (autre langue, ton plus détaillé, plusieurs questions par tour…).

## Modèles et effort

- **Défaut** : le code s'écrit avec la classe **standard**, effort `high`. La classe **forte** est réservée au
  diagnostic, à l'architecture et au cadrage. Si la session tourne avec la classe forte et que la tâche est d'écrire
  du code, je le dis avant de commencer.
- **Défaut** : effort maximal `high`, jamais au-delà.
- **Défaut** : les sous-agents et les missions qui écrivent du code utilisent la classe standard. Peu de sous-agents :
  un seul quand une lecture large le justifie.
- *Pour changer* : la correspondance type de tâche → classe → effort est dans [grille.md](grille.md) (c'est elle qui
  fait foi, et le lanceur en applique le plafond). Ici, tu ne règles que la politique générale.

## Quota et lancement

- **Défaut** : avant tout lancement, je présente un récapitulatif (projet, modèle, effort, durée max, consommation
  estimée en % de la fenêtre courte et en % de la limite hebdomadaire), puis j'attends un accord explicite.
- **Défaut** : je ne lance une mission que si la marge restante sur la fenêtre courte couvre l'estimation haute ;
  sinon je propose d'attendre la remise à zéro.
- **Défaut** : je relève la consommation avec l'outil de la plateforme quand il existe, sinon je la demande à
  l'utilisateur ; je ne l'invente jamais.
- **Défaut** : plusieurs missions en même temps seulement sur des **projets différents** et sur demande ; une seule à
  la fois par projet (cette dernière règle fait partie du socle).
- **Défaut** : en fin de semaine, si du quota hebdomadaire serait perdu à la remise à zéro, je propose de lancer des
  cartes « Prêt » de projets différents plutôt que de l'économiser.
- *Pour changer* : réécris la ligne. Budgets et durée maximale : `config.json`, clé `defauts`.

## Kanban (Orion)

- **Défaut** : 3 cartes « En cours » au plus, hors POC. Réglé dans `config.json`, clé `defauts.max_en_cours`.
- **Défaut** : en début de session, je lis la carte du chantier (colonne, « Prochaine étape », description) avant de
  commencer. Sans carte, je le dis et je n'en crée pas en lot sans ton accord.
- *Pour changer* : la limite, dans `config.json` ; le reste, ici.

## Fin de session

- **Défaut** : je mets à jour la carte (colonne et « Prochaine étape », jamais l'état du jour dans la description),
  j'ajoute un journal court « État au JJ/MM » dans le fichier d'axe du projet, et j'écris la ligne de fin dans
  `donnees/missions.jsonl`.
- **Défaut** : je propose le compactage vers 150 à 200 k jetons, avec la commande prête à coller. Je propose une
  nouvelle session au changement de sujet (ou après une pause d'une heure avec un gros historique), seulement si le
  relais est écrit.
- *Pour changer* : réécris la ligne (autre seuil de compactage, pas de journal…).

## Nova (facultatif)

- **Défaut** : 0 à 2 fichiers de méthode par brief, cités avec leur chemin ; la mission dit lesquels ont servi. Sans
  bibliothèque Nova configurée, j'ignore cette ligne.
- *Pour changer* : le nombre, ici ; l'index des méthodes, dans [nova.md](nova.md).

## Interdits ajoutés

Ici, tu **ajoutes** des interdits propres à toi ; tu n'en retires aucun du socle. Un interdit écrit ici s'applique à
Polaris et à ses missions dès la session suivante. Aucun n'est défini au départ ; décommente un exemple ou écris le
tien.

<!-- Exemples (à décommenter et adapter) :
- Ne jamais lire le dossier `clients/`.
- Pas d'appel à l'API de production.
-->

Retirer ou assouplir un interdit du **socle** demande de modifier `AGENTS.md` et `docs/garde-fous.md`, en connaissance
de cause : voir « Ce qui ne se retire pas » dans [../docs/installation.md](../docs/installation.md).
