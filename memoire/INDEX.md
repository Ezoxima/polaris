# Index général de la mémoire

Une ligne par projet et par axe. Chaque projet a son propre `memoire/INDEX.md` dans son dépôt ; ce fichier-ci est
la table des matières de l'ensemble. Polaris le lit pour savoir où trouver le contexte d'un projet **sans ouvrir
les projets eux-mêmes**.

Le contenu ci-dessous est un exemple fictif : remplace-le par tes projets. Les fichiers d'axe suivent le gabarit
`modeles/memoire-axe.md`.

| Projet | Axe | Fichier (dans le dépôt du projet) | Dernier état |
|---|---|---|---|
| boutique-web | catalogue | `memoire/catalogue.md` | JJ/MM : <une phrase> |
| boutique-web | paiement | `memoire/paiement.md` | JJ/MM : <une phrase> |
| pipeline-ventes | import | `memoire/import.md` | JJ/MM : <une phrase> |

Règles :

- Les fichiers d'axe vivent **dans le dépôt de chaque projet**, versionnés avec lui ; ils sont lisibles par
  Polaris, par les missions et par toute session, quelle que soit la plateforme.
- Une mission lit **un seul axe**, et la section de la variante concernée s'il y en a.
- La mémoire automatique d'un outil, quand elle existe, ne sert qu'aux préférences personnelles.
