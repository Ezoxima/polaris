# Journal des modifications

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; versions selon
[SemVer](https://semver.org/lang/fr/).

## [0.2.2] - 2026-11-25

Premier lot pour adapter Polaris à d'autres environnements : registres personnels réellement pris en compte, grille
alignée sur Copilot, et lanceur indépendant du Kanban. Les garde-fous ne sont pas affaiblis : il reste « une seule
mission à la fois par projet », le verrou du journal et le fichier `donnees/STOP`.

### Modifié

- Registres locaux : pour tout `registre/X.md`, un `registre/X.local.md` s'il existe le **remplace entièrement** (règle
  écrite dans `AGENTS.md`, rappelée dans `.github/copilot-instructions.md`, `docs/installation.md`,
  `docs/installation-restreinte.md` et `docs/architecture.md`). Chaque commande qui cite un registre renvoie à cette
  règle ; un test le vérifie. Aucun outil Python ne lit les registres : la règle est une consigne pour l'assistant.
- `registre/grille.md` : effort Copilot transmis par `--reasoning-effort` si l'aide du CLI le liste, crédits IA
  distincts du budget en dollars (`copilot.credits_ia_max`), nom de modèle vide = refus (et non plus « modèle par
  défaut ») ; une valeur `auto` est annoncée pour un lot suivant.
- `--parallele` ne « lève » plus rien : il lance seulement les missions du lot en même temps (un projet = une mission).
- `veille.py` affiche les cartes « En cours » d'Orion en note d'information, sans seuil ni alerte.
- `/go`, `/lancer`, `/point`, `registre/*.md`, README et docs : la règle des trois cartes est retirée.

### Supprimé

- Le plafond de cartes « En cours » : le lanceur ne lit plus Orion (plus de refus « trop de cartes » ni « Orion
  illisible »). `lire_cartes_orion`, `kanban.MAX_EN_COURS` et l'alerte `cartes:en_cours` disparaissent ; la clé
  `defauts.max_en_cours` quitte `config.exemple.json` et, si elle est encore présente, le lanceur l'annonce comme
  ignorée.

## [0.2.1] - 2026-11-25

Copilot, du clone neuf au premier lancement : options du CLI à jour, autorisation des outils clarifiée, parcours
« application seule » explicite, configuration pas à pas. Les garde-fous ne sont pas affaiblis.

### Ajouté

- `lancer_mission.py` (moteur `copilot`) : lecture de `copilot --help` au lancement (commande locale, sans service) et
  fonction pure `analyser_aide_copilot` ; transmission, seulement si l'aide les liste, de `--reasoning-effort` (effort
  du brief, valeur refusée si l'aide ne la liste pas), `--max-ai-credits` (réglage `copilot.credits_ia_max`, jamais
  converti depuis un budget en USD) et `--usage-output-file` (contenu résumé brut dans la sortie, le journal et le
  compte rendu, sans interpréter de champ).
- `copilot.autoriser_tous_outils` (`false` par défaut) : `--allow-all-tools` sur choix explicite, avec tous les
  `--deny-tool` conservés et un avertissement au `--dry-run` ; une mission qui réclame `--allow-all-tools` s'arrête
  avec une explication, sans relance. Risque documenté dans `docs/garde-fous.md`.
- `--dry-run` : options Copilot détectées et transmises.
- `.github/copilot-instructions.md` (renvoi vers `AGENTS.md`, garde-fous essentiels).
- `docs/copilot.md` : section « Application seule », tableau des options (dans l'aide / utilisée par le lanceur),
  essais supplémentaires. `docs/installation.md` : étape « 3 bis. Configurer Copilot ».

### Modifié

- Moteur `copilot` : un nom de modèle vide pour le modèle demandé refuse la mission en nommant
  `copilot.modeles.<modèle>` (auparavant : modèle par défaut, avec un simple avertissement) ; un projet absent de la
  config renvoie à l'étape d'installation.
- `config.exemple.json` : commentaire `_commentaire` (projets fictifs), `copilot.credits_ia_max` et
  `copilot.autoriser_tous_outils`.

### Limites

- Les options observées dans l'aide n'ont pas été essayées en mission réelle ; le format du fichier d'usage est
  inconnu ; la priorité de `--deny-tool` sur `--allow-all-tools` n'est pas éprouvée (essais listés dans
  `docs/copilot.md`).

## [0.2.0] - 2026-11-25

Installation en environnement restreint : un guide dédié, et des outils qui n'écrasent, ne lisent ni n'écrivent plus
que ce qu'ils annoncent.

### Ajouté

- `docs/installation-restreinte.md` : inventaire des capacités du poste (CLI d'agent, `gh`, Git, Python, tâches
  planifiées) avec ce qui marche sans elles et ce qui est différé ; Python hors du `PATH` ; dossier existant sans Git
  (sauvegarde, comparaison, fusion à la main, retour arrière) ; usage sans CLI ; Kanban existant ; tableau des accords
  distincts ; confidentialité de la personnalisation locale. Liens depuis le README et `docs/installation.md`.
- `generer_commandes.py --forcer` et le code de sortie 3 (voir « Corrigé »).
- `.gitignore` : `registre/*.local.md` pour la personnalisation locale.
- `registre/preferences.md` : réglage « Questions par tour » de l'entretien `creuser` (défaut : une seule).
- `commun.ErreurJournal` et `commun.Journal` (liste des événements avec les numéros des lignes illisibles).
- Tests pour chacun de ces points (350 au total).

### Modifié

- `/nouveau-projet` : le dossier, `git init`, le premier commit, l'inscription au Kanban et l'écriture au journal sont
  des étapes séparées, chacune avec son accord et sautable ; un dossier sans Git est un choix valide.
- `creuser` lit le nombre de questions par tour dans `registre/preferences.md` (une seule par défaut, au lieu de
  trois) ; `/note --creuser` suit le même réglage.
- `/conseil` et `creuser` ne promettent rien sur l'indépendance des avis, le nombre d'agents ou le coût, et ne lancent
  aucun agent ni n'écrivent aucune synthèse sans accord.
- `/point` lance la veille avec `--sans-ecrire` : la commande ne modifie plus rien, ce qu'elle annonce. Aucun outil ne
  relit `donnees/veille.json`, donc rien n'en dépend.
- `tests/test_confidentialite.py` : s'en tient aux fichiers suivis par Git ; hors dépôt Git, il écarte ce que
  `.gitignore` écarte.
- `kanban_init.py` : docstring à jour (la création réelle a été éprouvée le 25/11/2026).
- `pyproject.toml` : version 0.2.0.

### Corrigé

- `generer_commandes.py` écrasait un fichier cible écrit à la main. Désormais, un fichier cible existant sans la marque
  « Fichier généré par outils/generer_commandes.py » provoque un refus en bloc (code 3, liste des fichiers, rien
  d'écrit) sauf `--forcer` ; `--verifier` les signale à part. Un fichier qui porte la marque mais a été modifié à la
  main reste réécrit, comme avant.
- `veille.py --exemples` interrogeait quand même le Planificateur de tâches. Il ne fait plus aucune lecture système
  (ni Planificateur, ni Orion, ni `config.json`) ; l'aide et la docstring distinguent `--sans-ecrire` (pas d'écriture)
  de `--exemples` (pas de lecture système), deux options indépendantes.
- `commun.lire_journal` avalait les erreurs : un journal illisible donnait une liste vide, des lignes corrompues
  disparaissaient. Un journal absent reste vide ; une erreur d'E/S lève `ErreurJournal` (le lanceur refuse de lancer,
  la veille affiche une erreur de lecture) ; les lignes corrompues sont comptées et signalées avec leur numéro.
- `kanban_init.py` remplaçait un `config.json` invalide par l'exemple puis le réécrivait. Il refuse désormais (code 2,
  fichier intact) ; un `config.json` absent reste possible, mais l'outil l'annonce avant toute écriture.

### Pistes hors de ce lot

Lanceur automatique sans CLI d'agent (le mode 2 se remplace en attendant par une sous-session ouverte à la main, non éprouvée), connecteur vers un autre Kanban, contrat de données commun pour des journaux
existants, revue des comportements du lanceur (commit automatique, nouvelle tentative sur limite d'usage, dépassement
du plafond « En cours », verrou de 3 h). Notées dans la feuille de route du README.

## [0.1.2] - 2026-11-25

Corrections issues d'un test d'installation sur un clone vierge.

### Corrigé

- Une mission lancée depuis une session de l'app de bureau Claude Code plantait au premier lancement
  (`Failed to start inspector … EADDRINUSE`) : le `claude` enfant héritait de `BUN_INSPECT`. Le processus lancé par
  `outils/lancer_mission.py` reçoit désormais un environnement sans `BUN_INSPECT*` ni options `--inspect*` de
  `NODE_OPTIONS` (le reste de `NODE_OPTIONS` est conservé) ; le `--dry-run` signale ce qui est retiré.
- Le compte rendu de mission pouvait proposer une colonne inexistante (« Terminé ») : le pied de prompt liste
  désormais les six colonnes du Kanban, générées depuis `kanban.COLONNES`.

### Modifié

- Documentation : la création du tableau Orion a été essayée en réel le 25/11/2026 (README « Limites assumées »,
  `docs/installation.md` étape 4) ; précision que le `--dry-run` de `kanban_init.py` ne détecte pas un titre déjà pris ;
  ligne de dépannage pour `Failed to start inspector`.
- `pyproject.toml` : version 0.1.2.
- Tests : variables de débogueur (fonction pure, environnement réellement transmis, `--dry-run`) et colonnes du prompt.

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
