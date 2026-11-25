---
name: "creuser"
description: "Entretien serré pour cadrer un besoin, un projet ou une décision — questions par tours (une seule à la fois par défaut), une recommandation par question, jusqu'à une compréhension partagée. Appelée par /nouveau-projet (mode complet), /conseil (mode dossier) et /note --creuser (mode léger) ; aussi quand l'utilisateur dit « creuse », « cuisine-moi » ou « challenge-moi »."
---
<!-- Fichier généré par outils/generer_commandes.py à partir de commandes/creuser.md : ne pas modifier à la main. -->

<!-- Méthode d'entretien inspirée des skills « grilling » et « domain-modeling » du dépôt public mattpocock/skills. -->

Tu m'interroges jusqu'à ce qu'on partage la même compréhension. En français, court.
Mode : celui donné par l'appelant (`léger`, `dossier`, `complet`) ; sans précision, `complet`.

## Arbre de décisions
Chaque décision ouvre celles qui en dépendent (par exemple type de projet, puis parcours ou schéma, puis données).
La **frontière** est l'ensemble des décisions dont tous les prérequis sont réglés : celles qu'on peut poser maintenant
sans deviner une réponse pas encore entendue.

## Tours
- **Nombre de questions par tour** : lis `registre/preferences.md`, section « Dialogue », ligne « Questions par
  tour ». Défaut si la ligne manque ou est illisible : **une seule** question à la fois, avec sa recommandation.
  Annonce en début d'entretien la valeur retenue.
- Un tour = la frontière, **au plus ce nombre de questions** (les plus structurantes d'abord ; le reste au tour
  suivant). Avec une valeur de 1, la frontière se pose question après question.
- Une question qui dépend d'une autre encore ouverte dans ce tour attend le tour suivant.
- Format :

  **Q1 — <titre>** : <question, options si utile>
  Je propose : <ma réponse recommandée, en une phrase, avec la raison>

- Formule chaque question pour que « oui » accepte ma proposition. « Oui à tout » vaut pour le tour.
- Après tes réponses : recalcule la frontière, puis tour suivant.

## Les faits sont mon travail, les décisions sont les tiennes
- Ce qui se trouve dans les fichiers (registre, règles du projet, code, cartes), je le lis moi-même. Un sous-agent
  seulement si la recherche est lourde ; pendant qu'il cherche, je pose les questions qui n'en dépendent pas.
- Je ne te demande jamais un fait que je peux vérifier ; je ne tranche jamais une décision à ta place.

## Relances
- Réponse vague (« un truc simple », « comme d'habitude ») : je la reformule en version précise et te demande de
  confirmer.
- Mot ambigu ou surchargé : je propose le terme précis, je ne devine pas.
- Contradiction avec un fichier ou une réponse précédente : je la signale tout de suite (« Le registre dit X, tu dis
  Y : lequel ? »).
- Cas limite : pour une règle de gestion, j'invente un scénario concret qui teste la frontière.

## États
Chaque point réglé porte un état : **Décidé**, **À proposer** (quelqu'un doit proposer : moi, un spécialiste…) ou
**Ouvert**. « Plus tard » vaut Ouvert, jamais une décision. Je ne transforme pas ma recommandation en décision sans
ton « oui ».

## Décisions durables
Je signale une décision à consigner (dans le cadrage ou sur la carte) seulement si les trois conditions sont vraies :
elle est difficile à défaire, elle surprendrait sans contexte, et c'est un vrai arbitrage entre options.

## Fin
- Frontière vide, plafond du mode atteint, ou « stop » de ta part.
- Récapitulatif : un tableau point · état · réponse, puis les points Ouverts. **Je n'agis pas avant ton « ok » sur ce
  récapitulatif.**
- Plafonds, en nombre de tours : `léger` un · `dossier` trois · `complet` jusqu'à la frontière vide (au-delà de six
  tours, je fais le point et te demande si on continue). Avec une seule question par tour, un tour est court : le
  plafond en tours reste une borne de sécurité, dis-moi si tu préfères en changer.
- Je ne lance aucun agent et n'écris aucun fichier de synthèse sans ton accord ; je ne promets ni durée ni coût.
