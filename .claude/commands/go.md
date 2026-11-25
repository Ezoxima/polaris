---
description: "Lance un ou plusieurs briefs déjà écrits (m-AAAAMMJJ-NN-xxxx) via outils/lancer_mission.py"
argument-hint: "<m-AAAAMMJJ-NN-xxxx> [autres identifiants] [--parallele] [--moteur claude|copilot]"
---
<!-- Fichier généré par outils/generer_commandes.py à partir de commandes/go.md : ne pas modifier à la main. -->

Missions : `$ARGUMENTS`. Tu es l'orchestrateur : **tu n'écris pas de code dans les projets** ; tu lances des briefs
déjà écrits (`/lancer` rédige le brief d'une carte, `/go` lance un brief qui existe).

## 1. Vérifier avant de lancer
- Chaque identifiant a un brief : `briefs/<id>.md`. Sinon, dis-le et propose `/lancer`.
- Relis la ligne « Exécution » et le « Périmètre » de chaque brief : si l'un touche à l'argent réel, au `git push`,
  à une commande administrateur, à un mot de passe, à une base de production, à une suppression de données ou à une
  tâche planifiée, **refuse et passe en mode 3** (l'outil vérifie les paramètres du brief, pas son sens).
- Une seule variante par mission ; le modèle fort a un effort plafonné ; le code s'écrit avec la classe standard.
- Dry-run d'abord : `python outils/lancer_mission.py <id> [<id2> …] [--parallele] --dry-run`. Il affiche le dossier
  de travail, le modèle, l'effort, les outils autorisés, la durée et le budget, les conflits du lot, et refuse
  proprement (brief introuvable, projet absent de `config.json`, mode différent de 2, autre mission en cours **sur le
  même projet**, trop de cartes « En cours » hors POC, Orion illisible, fichier `donnees/STOP`).

## 2. Récapitulatif et accord
Affiche, par mission : projet, carte, variante, modèle, effort, durée max, budget, **consommation estimée**
(`registre/grille.md`). Relève la consommation actuelle (outil de la plateforme, sinon demande-la-moi) : ce sont les
« avant » du journal. **Attends mon accord explicite.**

## 3. Lancer
- `--parallele` : seulement sur ma demande, pour des projets différents (deux missions d'un même projet sont refusées) ;
  il lève le plafond des trois cartes « En cours » ; le récapitulatif donne la consommation cumulée.
- `python outils/lancer_mission.py <id> [<id2> …] [--parallele] [--moteur …]`, en arrière-plan quand l'outil de la
  plateforme le permet. La sortie est préfixée par l'identifiant et se termine par une ligne « Bilan ». Le lanceur
  écrit `lancee` puis `terminee`, `echouee` ou `arretee` au journal, et le compte rendu dans
  `briefs/<id>-compte-rendu.md`. Arrêt d'urgence : créer le fichier `donnees/STOP`.
- Les cartes ne bougent pas toutes seules : mets-les à jour à la fin.

## 4. À la fin : toujours vérifier, ne pas croire le compte rendu
- Relance les tests et le lint du projet, relis `git status`, `git log` et `git diff --stat` (aucune référence
  distante changée, aucun fichier hors périmètre).
- Carte : colonne, « prochaine étape », consommation mesurée, description corrigée si elle est devenue fausse.
- Journal d'axe du projet (« État au JJ/MM ») ; ligne `mesure` au journal avec les pourcentages d'après.
- Dis-moi : fait ou partiel, ce qui reste à décider, et les refus de permission.

Ne modifie aucun projet toi-même.
