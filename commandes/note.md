---
type: commande
description: Transforme une idée en carte « À cadrer » dans Orion (y compris une idée de POC)
argument-hint: <l'idée en une phrase> [--creuser]
---

Idée : {{arguments}} (si c'est vide, demande-la).

**Kanban d'abord** : lis `kanban.mode` dans `config.json` avant toute lecture ou écriture d'Orion. `github` : suis les étapes ci-dessous (lecture des cartes puis création dans Orion). `manuel` : aucune lecture ni écriture d'Orion : montre la fiche de la carte prévue (étapes 1 et 3) à recopier dans mon outil, et ne crée rien. `aucun` : aucune carte : dis-le, propose de garder l'idée dans une phrase de `CADRAGE.md` ou dans un brief, et ne crée rien. Clé absente : traite comme `github` (compatibilité) et dis-le en une ligne.

Option `--creuser` dans les arguments : avant l'étape 3, mène un tour de la skill `creuser` en mode `léger` (un tour,
au plus le nombre de questions réglé dans `registre/preferences.md` (ou sa version `.local.md`, voir AGENTS.md) et reporte son récapitulatif dans la description de la carte. Sans l'option, reste à une
question au plus.

1. Déduis sans insister : **Projet** (liste dans `registre/projets.md` (ou sa version `.local.md`, voir AGENTS.md) ; « Transverse » si plusieurs),
   **Variante** seulement si le projet en a (une seule par carte : si l'idée en couvre plusieurs, propose une carte
   par variante), **Nature** (Chantier · Démarche · Décision · Script · POC ; une idée floue de nouveau projet
   est un POC, sinon un Chantier), **Taille** (XS à XL, au jugé). Un mot ambigu ou un projet incertain : pose
   **une** question, ne devine pas.
2. Vérifie qu'aucune carte existante ne la couvre déjà (lecture des cartes, `registre/kanban.md` (ou sa version `.local.md`, voir AGENTS.md) ; sinon propose
   de compléter l'existante.
3. Montre la carte prévue (titre clair en français, champs, prochaine étape « Cadrer : … », **description** selon
   le modèle de `registre/kanban.md` : contexte, objectif et « fait quand », pointeurs) et crée-la dans **À
   cadrer** après mon « ok » (une phrase suffit), avec `--body`. Recettes : `registre/kanban.md`.
4. Confirme avec le lien du tableau. Ne lance aucun travail.
