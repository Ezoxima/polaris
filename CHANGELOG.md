# Journal des modifications

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; versions selon
[SemVer](https://semver.org/lang/fr/).

## [0.1.1] - 2026-11-25

### Ajouté

- `registre/preferences.md` : les choix par défaut (dialogue, modèles et effort, quota et lancement, Kanban, fin de
  session, Nova) regroupés dans un seul fichier, avec « comment changer » pour chacun, et une section
  « Interdits ajoutés » (on y ajoute des interdits, on n'en retire pas).
- `docs/installation.md` : section « Personnaliser Polaris » (quoi, où, comment) et rappel de ce qui ne se retire pas.
- `requirements-dev.txt` : pytest et ruff à versions fixées, utilisé par l'intégration continue.
- Tests : `preferences.md`, renvoi depuis `AGENTS.md`, versions épinglées et usage par la CI.

### Modifié

- Les préférences de travail (mot ambigu, récapitulatif avant lancement, parallélisme sur demande, économie de quota,
  fin de session) quittent `AGENTS.md` pour `registre/preferences.md` ; `AGENTS.md` y renvoie. Les garde-fous restent
  dans `AGENTS.md`.
- `pyproject.toml` : version 0.1.1 ; le groupe optionnel `dev` est retiré, `requirements-dev.txt` devient la seule source.
- Intégration continue : installation par `pip install -r requirements-dev.txt`.

## [0.1.0] - 2026-11-25

Première version publique.

### Ajouté

- Noyau `AGENTS.md` (lu par Copilot et par Claude Code) et `CLAUDE.md` (importe `AGENTS.md`).
- Registre : fiches de projets, grille modèle / effort, formats de brief, de compte rendu et de journal, modèle de
  cadrage, recettes du Kanban, index facultatif de méthodes.
- Gabarits de brief, de compte rendu et de mémoire d'un axe ; index général de la mémoire.
- Sept commandes (`/point`, `/quoi-faire`, `/note`, `/lancer`, `/go`, `/nouveau-projet`, `/conseil`) et la skill
  `creuser`, écrites une fois dans `commandes/` et générées pour Claude Code (`.claude/`) et pour Copilot
  (`.github/skills/`).
- `outils/kanban_init.py` : création du tableau Orion (`--dry-run`, refus si un tableau existe, aucune suppression).
- `outils/lancer_mission.py` : missions en séquence ou en parallèle, une seule par projet, moteurs `claude` et
  `copilot`, journal JSONL, compte rendu, contrôle de la référence distante git.
- `outils/veille.py` : échéances, missions sans fin, cartes « En cours », tâches planifiées Windows ; sans quota.
- `outils/generer_commandes.py` (avec `--verifier`) et `outils/nouvel_id.py`.
- Documentation : architecture, installation, correspondance Copilot (documenté et non testé), garde-fous.
- Tests pytest, test de confidentialité sur tous les fichiers suivis, intégration continue (ruff, pytest, commandes
  générées ; Ubuntu et Windows, Python 3.11 à 3.13).

### Limites connues

- Le moteur Copilot et la création réelle du tableau Orion n'ont pas été essayés ; voir `docs/copilot.md`.
