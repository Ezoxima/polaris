---
description: "Où j'en suis partout — alertes, en cours, échéances, quota"
model: "haiku"
---
<!-- Fichier généré par outils/generer_commandes.py à partir de commandes/point.md : ne pas modifier à la main. -->

Fais le point sur tous mes projets : court (25 lignes au plus), en français clair, sans lire de plan de reprise.

1. Lis Orion (recettes : `registre/kanban.md`) : toutes les cartes.
2. Lis `registre/projets.md` (échéances, tâches planifiées) et les 5 dernières lignes de `donnees/missions.jsonl`.
   Lance `python outils/veille.py --sans-ecrire` : elle lit ses sources, n'écrit aucun fichier et ne crée aucune carte
   ni aucune tâche.
3. Réponds dans cet ordre :
   - **Alertes** (sortie de la veille ; critiques d'abord, puis attention, puis info ; « aucune » si vide ; signale
     les lignes `!` d'erreur de lecture). Pour chaque alerte **sans** carte existante, propose une carte (titre,
     champs, prochaine étape) et ne la crée qu'après mon « ok », avec la procédure de `/note`. Pour une alerte qui
     cite une carte existante, cite-la et n'en propose pas.
   - **En cours** : chaque carte avec sa prochaine étape ; signale s'il y en a plus de trois hors POC.
   - **Échéances proches** (14 jours au plus) et tâches planifiées connues en panne.
   - **Bloqué ou en attente** : une ligne chacune, avec ce qui débloque.
   - **Dernière mission** et son état (une mission lancée sans ligne de fin depuis plus de 90 minutes est suspecte :
     signale-le).
   - **Quota** : relève la consommation (fenêtre courte et limite hebdomadaire) avec l'outil de la plateforme s'il
     en existe un ; sinon demande-la-moi. Ne l'invente jamais.
4. Termine par une seule question : « Je te propose 2 ou 3 cartes ? » (`/quoi-faire`).

Ne modifie rien.
