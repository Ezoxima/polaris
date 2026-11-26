# Format de mission

## Brief (envoyé à la session, autoportant)

```
Carte : <titre> (<colonne>) — Variante : <valeur ou —> — Projet : <nom exact du registre>
Objectif : <une phrase>
Prochaine étape : <…>
Critère de fin : <vérifiable>
Méthodes (0 à 2) : <chemin d'un fichier de méthodes, ou « aucune »>
Lire d'abord : <AGENTS.md ou CLAUDE.md du projet, memoire/<axe>.md, spécification…>
Périmètre : autorisé <…> · interdit <…> · permissions anticipées <…>
Exécution : modèle <haiku|sonnet|opus> · effort <low|medium|high> · mode <1|2|3> · durée max <N min> · conso estimée <% fenêtre / % hebdo>
```

Gabarit vide : `modeles/brief.md`.

Règles :

- **Autoportant** : la session ne voit que le brief et le dossier de son projet. Elle ne peut pas lire Polaris.
- Une seule **variante** par mission. La première ligne doit respecter le format ci-dessus : le lanceur la lit.
- La ligne « Exécution » doit contenir le modèle, l'effort, le mode et la durée max. Un budget peut s'ajouter
  (`· budget 6 USD`) ; sans budget, le lanceur le calcule à partir de la durée.
- Aucun secret recopié (nom seulement). Aucun contenu de message ou de ticket : une référence suffit.
- Le `AGENTS.md` ou le `CLAUDE.md` du projet prime. Voir les garde-fous : [../docs/garde-fous.md](../docs/garde-fous.md).
- Les méthodes (0 à 2) viennent d'une bibliothèque facultative (voir `nova.md`) ; chaque chemin cité doit exister.

Un identifiant se réserve avec `python outils/nouvel_id.py` : il renvoie `m-AAAAMMJJ-NN-xxxx` (`xxxx` aléatoire) et
crée `briefs/<id>.md` en création exclusive, donc deux sessions ne partagent jamais un identifiant.

## Lancement

```
python outils/lancer_mission.py m-AAAAMMJJ-NN-xxxx [autres ids] [--moteur claude|copilot] [--parallele] [--dry-run]
```

- Sans option : les missions s'enchaînent l'une après l'autre ; la chaîne s'arrête à la première qui n'est pas
  « terminée ».
- `--parallele` : les missions partent en même temps. **Un seul projet à la fois** : deux missions du même projet
  sont refusées avant tout lancement.
- `--dry-run` : affiche ce qui serait lancé et les contrôles, sans rien lancer ni rien écrire.
- Les paramètres de chaque projet (dossier, dépôt git, outils autorisés) viennent de `config.json`.
- `donnees/STOP` (fichier vide) : plus aucune nouvelle mission ne démarre ; celles en cours finissent.

## Compte rendu (exigé en fin de session)

Gabarit : `modeles/compte-rendu.md`.

- Ce qui a été fait, avec les preuves : tests et, **avec un dépôt git suivi**, le commit local et `git status` ;
  sans dépôt, la liste des fichiers modifiés.
- La carte mise à jour (colonne et « prochaine étape ») : section « Carte » avec `kanban.mode` à `github` ;
  « Kanban (à reporter à la main) » en `manuel` (rien ne la lit) ; aucune section en `aucun`.
- Le journal de session ajouté au fichier d'axe (section « État au JJ/MM », 5 à 10 lignes).
- Ce qui reste à décider par l'utilisateur.
- La permission manquante, s'il y en a eu une : laquelle et pourquoi.
- La consommation relevée avant et après, si la plateforme l'affiche.

Le lanceur écrit le compte rendu dans `briefs/<id>-compte-rendu.md`, précédé d'un en-tête (statut, durée, coût,
refus de permission, commits créés, état de l'arbre git). Un compte rendu existant est archivé, jamais écrasé.

Voies sans lanceur (`prompt`, `sous_session`) : l'utilisateur enregistre lui-même le compte rendu et la fin de mission avec
`python outils/lancer_mission.py <id> --terminer --compte-rendu <fichier> --voie prompt|sous_session` (aucun moteur
lancé, aucun contrôle du lanceur ; la ligne `terminee` porte la voie et `moteur_vise`).

## Journal : `donnees/missions.jsonl`

Une ligne JSON par événement.

| Champ | Contenu |
|---|---|
| `ts` | horodatage ISO 8601 (UTC) |
| `evenement` | `creee`, `preparee`, `lancee`, `terminee`, `echouee`, `arretee`, `permission_manquante` ou `mesure` |
| `mission` | identifiant `m-AAAAMMJJ-NN-xxxx` |
| `projet`, `carte`, `variante` | repères (`variante` peut être `null`) |
| `modele`, `effort`, `mode` | le couple choisi et le mode 1, 2 ou 3 |
| `moteur` | `claude` ou `copilot` : le moteur **lancé** (lignes `lancee`, `terminee`, `echouee`, `arretee`) |
| `moteur_vise` | lignes `preparee` et `terminee` des voies sans lanceur : le moteur **visé** (`--moteur`, sinon `moteur_par_defaut`, sinon `claude` par défaut ; la source est dite dans `note`), qui règle la liste d'outils du prompt ; aucun moteur n'est lancé dans cette voie, d'où un champ distinct de `moteur` |
| `voie` | `cli` (lanceur), `prompt` ou `sous_session` (voies sans lanceur, événement `preparee`) |
| `modele_reel` | Copilot seulement : `currentModel` du fichier d'usage, ou « non relevé » (jamais déduit) ; `modele` reste la classe demandée |
| `session_id` | identifiant de la session, si la plateforme le donne |
| `conso_avant`, `conso_apres` | consommation relevée (la fenêtre courte, en %) |
| `conso_hebdo_avant`, `conso_hebdo_apres` | consommation hebdomadaire relevée (en %) |
| `note` | une phrase, **jamais de secret** |

Le lanceur écrit `lancee`, puis `terminee`, `echouee` ou `arretee`. `lancer_mission.py --prompt` écrit `preparee` : un
prompt a été préparé, **rien n'a été lancé** ; le lancement et la fin de cette voie se notent à la main. Les lignes
`creee`, `mesure` et `permission_manquante` sont écrites par Polaris ou à la main.
