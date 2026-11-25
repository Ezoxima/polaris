---
name: "quoi-faire"
description: "Propose 2 ou 3 cartes selon mon temps ou mon envie, avec leur consommation estimée"
argument-hint: "<temps disponible ou envie, par exemple \"1 h\", \"soirée\", \"envie de données\">"
---
<!-- Fichier généré par outils/generer_commandes.py à partir de commandes/quoi-faire.md : ne pas modifier à la main. -->

Entrée : le texte que j'écris après le nom de la commande (un temps ou une envie ; si c'est vide, demande-le en une question).

1. Lis Orion (`registre/kanban.md` ou sa version `.local.md`, voir AGENTS.md), colonnes **En cours** puis **Prêt** (les cartes « En attente » dont la
   condition est levée aussi). Lis `registre/grille.md` (ou sa version `.local.md`, voir AGENTS.md) pour la consommation, et relève la consommation actuelle
   avec l'outil de la plateforme s'il en existe un ; sinon demande-la-moi.
2. Filtre : taille compatible avec le temps (XS ≈ 20 min, S ≈ 1 h, M ≈ une soirée ; L et XL jamais d'un bloc :
   propose la première étape) ; l'envie oriente le projet ; jamais une carte « En pause » ou « À cadrer », sauf une
   décision rapide (nature Décision, taille XS ou S).
3. Priorité : (1) une échéance datée proche, (2) une carte déjà « En cours », (3) ce qui débloque le plus de
   cartes, (4) ce que je repousse depuis longtemps.
4. Réponds avec **2 ou 3 cartes**, une ligne chacune : titre · projet · taille · pourquoi maintenant · mode (1, 2
   ou 3) · classe de modèle et effort selon la grille · **consommation estimée** ; avertis si elle dépasse ce qui
   reste. Une carte qui touche l'argent réel, une tâche planifiée, les droits administrateur ou une base de
   production passe en mode 3 : dis-le.
5. Ajoute « Dis-moi laquelle, je prépare le brief (`/lancer`) ». Ne lance rien.

Ne modifie rien.
