# Index des méthodes (Nova), facultatif

Nova est une bibliothèque de méthodes (agents, skills) que Polaris consulte quand une tâche le justifie : relecture,
méthode de cadrage, patron d'architecture. **Polaris fonctionne sans.** Le dépôt public
[ECC](https://github.com/affaan-m/ECC) en est un exemple.

Règles d'usage :

- La bibliothèque est clonée **en lecture seule** : jamais de modification ni de mise à jour sans l'accord de
  l'utilisateur.
- Polaris choisit **0 à 2 fichiers** par mission, les lit, vérifie que les outils et chemins qu'ils supposent
  existent, puis les cite avec leur chemin dans le brief (ligne « Méthodes »).
- Un fichier introuvable ou inutilisable est signalé, jamais prétendu appliqué.
- Le `AGENTS.md` ou le `CLAUDE.md` du projet prime en cas de conflit.
- Rien n'est copié ni chargé en bloc.

Index : une ligne par fichier utile à tes technologies. Les chemins ci-dessous sont des exemples à remplacer.

| Besoin | Fichier (relatif au clone) | Quand l'utiliser |
|---|---|---|
| Relecture de code Python | `agents/python-reviewer.md` | après une mission qui modifie du Python |
| Commits atomiques et messages | `skills/git-workflow/SKILL.md` | mission qui crée des commits |
| Publier un projet privé | `skills/opensource-pipeline/SKILL.md` | assainir avant de rendre un dépôt public |
