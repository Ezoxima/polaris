# Orion : recettes `gh`

Orion est un tableau GitHub Projects. Ces recettes servent aux commandes de `commandes/`. Les identifiants du
tableau (numéro, propriétaire, id du projet, id des champs et des options) ne sont **pas** dans ce fichier : ils
sont dans `config.json`, clé `kanban`, écrits par `python outils/kanban_init.py`. Ce sont des repères, pas des
secrets, mais ils sont propres à ton tableau ; `config.json` n'est pas versionné.

Dans les commandes ci-dessous : `<proprietaire>` et `<numero>` viennent de `kanban.proprietaire` et
`kanban.numero` ; `<projet_id>` de `kanban.projet_id` ; `<id champ>` et `<id option>` de `kanban.champs`.

Prérequis : `gh` installé et connecté, avec le droit `project` (`gh auth refresh -s project`).

## Colonnes et champs

Colonnes du champ `Status` : **À cadrer · Prêt · En cours · En attente · En pause · Fait**.

| Champ | Type | Valeurs |
|---|---|---|
| Status | choix unique | les six colonnes ci-dessus |
| Nature | choix unique | Chantier, Démarche, Décision, Script, POC |
| Taille | choix unique | XS, S, M, L, XL |
| Phase | choix unique | POC, MVP, Produit final |
| Projet | texte | nom du projet, tel que dans `registre/projets.md` (« Transverse » si plusieurs) |
| Prochaine étape | texte | une phrase |
| % 5 h | nombre | consommation estimée ou mesurée (fenêtre courte) |
| % hebdo | nombre | consommation estimée ou mesurée (limite hebdomadaire) |
| Variante | texte | facultatif ; créé par `kanban_init.py --avec-variante` |

« Type » est un nom réservé par GitHub : le champ s'appelle **Nature**. Le champ **Projet** est un **texte** et non
un choix : ajouter une option à un champ à choix unique change tous les identifiants d'options et efface la valeur
des cartes existantes.

## Recettes

- **Lire toutes les cartes** :
  `gh project item-list <numero> --owner <proprietaire> --format json --limit 500`
  → `items[]` avec `id`, `title`, `status`, `nature`, `taille`, `phase`, `projet`, `prochaine étape`, `% 5 h`,
  `% hebdo`, et `content` = `{id, title, body, type}` (la description est dans `content.body`). Au-delà de 500
  cartes, la lecture est tronquée : le lanceur le signale.
- **Créer une carte avec sa description** :
  `gh project item-create <numero> --owner <proprietaire> --title "<titre>" --body "<description>" --format json`
  → `id` de la carte, puis renseigner les champs. Toute carte naît avec une description ; jamais de carte vide.
- **Changer la description d'une carte** :
  `gh project item-edit --id <content.id> --title "<titre actuel>" --body "<description>"`. L'identifiant est celui
  du **brouillon** (`content.id`), pas celui de la carte ; toujours repasser `--title`, sinon le titre risque d'être
  effacé.
- **Changer un choix** :
  `gh project item-edit --id <id carte> --project-id <projet_id> --field-id <id champ> --single-select-option-id <id option>`
- **Texte** : `… --field-id <id champ> --text "<phrase>"` · **nombre** : `… --field-id <id champ> --number <n>`
- **Plusieurs champs d'un coup** : une seule requête `gh api graphql` avec un alias `updateProjectV2ItemFieldValue`
  par champ (plus rapide et plus économe qu'un appel `gh` par champ).
- **Vérifier la connexion** : `gh auth status`.

## Modèle de description d'une carte

Les cartes sont des **brouillons**, sans dépôt lié : pas d'issue, donc pas de fil de discussion. La description
porte tout le contexte ; l'état qui bouge va dans « Prochaine étape » et dans le journal d'axe du projet.

```
**Contexte**
Pourquoi cette carte existe, en 1 à 3 phrases, avec ce qui est déjà acquis.

**Objectif / fait quand**
Ce qu'on veut obtenir et le critère qui permet de dire « Fait ».

**Pointeurs**
Fichiers, plans, spécifications, cartes liées (chemins relatifs au dépôt du projet).

**Garde-fous**   (seulement si le projet en impose : argent réel, production, données privées…)
```

Rien de secret dans une description (ni jeton, ni mot de passe, ni donnée bancaire). Ne pas y recopier l'état du
jour : il se périme.

## Règles

- Pas de plafond de cartes « En cours » : le lanceur ne lit pas Orion. Seule règle mécanique : une seule mission à la
  fois par projet.
- Un POC ne se lance jamais directement : il passe par `/note` (carte « À cadrer »).
- Jamais de suppression de carte sans demande explicite de l'utilisateur.
- Titres en français clair.
