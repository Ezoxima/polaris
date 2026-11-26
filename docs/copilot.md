# Polaris avec GitHub Copilot

La documentation de Copilot évolue vite. Cette page n'emploie que **trois mentions**, les mêmes partout (ici, dans
le README et dans les autres guides) :

| Mention | Sens |
|---|---|
| **documenté** | dit par l'aide du CLI ou par la documentation officielle (sources ci-dessous, consultées le 25 novembre 2026) |
| **observé** | constaté par un essai sur un poste, avec la **version citée** (application ou CLI) ; sans version citée, elle n'a pas été relevée |
| **non testé** | ni l'un ni l'autre : aucune mission n'a été lancée de bout en bout avec Copilot |

« Observé » vaut pour la version citée, sans garantie pour les suivantes ; « documenté » ne dit pas que l'option a été
essayée en mission réelle.

Deux façons d'utiliser Copilot avec Polaris : [l'application seule](#application-seule-sans-cli) (conversation, sans
ligne de commande) et [le CLI](#le-moteur-copilot-du-lanceur) (le lanceur de missions).

## Sources consultées

- Instructions de dépôt : [add-repository-instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions),
  [matrice de prise en charge](https://docs.github.com/en/copilot/reference/custom-instructions-support) et
  [instructions dans VS Code](https://code.visualstudio.com/docs/copilot/customization/custom-instructions).
- Fichiers de prompt : [prompt-files](https://code.visualstudio.com/docs/copilot/customization/prompt-files).
- Skills : [about-agent-skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) et
  [agent-skills dans VS Code](https://code.visualstudio.com/docs/copilot/customization/agent-skills).
- Agents personnalisés : [create-custom-agents](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/create-custom-agents).
- Copilot CLI : [référence programmatique](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference),
  [référence des commandes](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference)
  et [dépôt du CLI](https://github.com/github/copilot-cli).

## Application seule (sans CLI)

Tu as l'application Copilot et pas de ligne de commande : tout ce qui est conversationnel marche (le noyau, les
commandes `/point`, `/note`…) ; le lanceur automatique, non.

**Ce que l'application charge.**

| Fichier | Statut |
|---|---|
| `.github/copilot-instructions.md` | **Documenté** : instructions de dépôt lues par Copilot. Fourni ici : court, il renvoie à `AGENTS.md` et rappelle les garde-fous essentiels. **Observé** (application 1.5.0) : chargé d'office, comme `AGENTS.md` |
| `AGENTS.md` | **Observé** (application 1.5.0) : l'application a restitué des mots témoins de ce fichier sans appel d'outil, donc il est chargé d'office. **Documenté** aussi pour le CLI, VS Code et l'agent de code cloud |
| `.github/skills/<nom>/SKILL.md` | **Documenté** : les commandes de Polaris (`/point`, `/lancer`…) y sont générées depuis `commandes/`. Ne les modifie pas à la main. **Observé** (application 1.5.0) : les skills sont listées et exécutées par l'application (`configurer` et `point` essayées : une question à la fois, diff montré avant écriture, aucun fichier modifié par `/point`). **Non testé** : leur affichage dans le menu `/` |

**L'essai pour le vérifier** (2 minutes ; les deux fichiers ont été observés comme chargés dans l'application 1.5.0, refais-le si ta version change). Ouvre le dossier Polaris dans l'application et pose une question dont la
réponse n'est que dans `AGENTS.md`, par exemple : « Quels sont les trois modes d'aiguillage de Polaris, et lequel
sert à une analyse ? » (réponse attendue : mode 1, un sous-agent en lecture seule). Une réponse juste montre que
`AGENTS.md` est lu, ou que `copilot-instructions.md` a suffi à t'y renvoyer ; une réponse vague ou inventée montre que
l'application ne charge ni l'un ni l'autre : dans ce cas demande-lui de lire `AGENTS.md` au début de chaque session,
et note le résultat ici.

**Mode 2 sans CLI.** Le lanceur appelle une CLI. Sans elle, `python outils/lancer_mission.py --prompt <id>` écrit un
prompt autonome (`briefs/<id>-prompt.md`) que tu colles dans une nouvelle session ; l'application sait aussi créer une
sous-session avec ce prompt (**observé** : le prompt a été reçu par une vraie sous-session ; une mission complète en sous-session sur un projet fictif est **observée** : réussie, compte rendu et ligne `terminee` saisis à la main, sans aucun contrôle du lanceur), mais **elle ne garantit aucun des contrôles du
lanceur** : voir [architecture.md, « Mode 2 par paliers »](architecture.md#mode-2-par-paliers) et
[installation-restreinte.md](installation-restreinte.md#4-sans-cli-dagent-lapplication-seulement).

## Correspondance Claude Code et Copilot

| Brique de Polaris | Côté Claude Code | Côté Copilot | Statut |
|---|---|---|---|
| Noyau (rôle, aiguillage, garde-fous) | `CLAUDE.md`, qui importe `AGENTS.md` | `AGENTS.md` à la racine, et `.github/copilot-instructions.md` qui y renvoie | **Documenté** : `AGENTS.md` est lu par Copilot CLI, par VS Code (Copilot Chat), par l'agent de code cloud et la revue de code ; **observé** dans l'application seule (1.5.0, voir plus haut) |
| Instructions propres à Copilot | — | `.github/copilot-instructions.md` | **Documenté** ; fourni, court (renvoi vers `AGENTS.md`) |
| Règles par dossier | `CLAUDE.md` secondaires | `AGENTS.md` du dossier le plus proche (documenté) ou `.github/instructions/*.instructions.md` avec `applyTo` | **Documenté**, non utilisé par Polaris |
| Commandes (`/point`, `/lancer`…) | `.claude/commands/<nom>.md` | skills `.github/skills/<nom>/SKILL.md` | **Documenté** : le front matter exige `name` (identique au dossier) et `description` ; VS Code appelle une skill par `/nom`. **Observé** (application 1.5.0) : skills listées et exécutées. **Non testé** : passage d'argument après le nom, menu `/` |
| Skill `creuser` | `.claude/skills/creuser/SKILL.md` | `.github/skills/creuser/SKILL.md` | **Documenté**, **non testé**. La page GitHub dit que Copilot lit aussi `.claude/skills/` : la skill peut alors apparaître deux fois |
| Fichiers `.prompt.md` | — | non générés | **Documenté** : réservés aux sessions « Local » de VS Code, et ce mode est annoncé comme déprécié (retrait prévu en février 2027) ; la page recommande les skills |
| Mode 1 (sous-agent en lecture seule) | outil `Agent` | agent personnalisé `.github/agents/<nom>.agent.md` avec `tools` restreints | **Documenté** (emplacement, front matter). **Non fourni** en v1 |
| Mode 2 (mission sans fenêtre) | `claude -p` | `copilot -p` | Voir ci-dessous. **Non testé** |
| Mode 3 (session interactive) | session normale | session normale de Copilot | Sans objet |
| Modèle | `--model` | `--model=MODELE`, ou variable `COPILOT_MODEL` | **Documenté**. Les noms se déclarent dans `config.json` (`copilot.modeles`, obligatoire pour lancer) ; la valeur `auto` est **documentée** et **observée** (CLI 1.0.98), possible si l'aide de ta version la documente (voir plus bas) |
| Effort | `--effort` | `--reasoning-effort` | **Observé** dans l'aide d'une version récente, pas dans la référence ; utilisé seulement si l'aide l'affiche (voir le tableau des options) |
| Budget | `--max-budget-usd` | `--max-ai-credits` (crédits IA, **pas des USD**) | **Observé** ; réglage `copilot.credits_ia_max`, jamais converti depuis un budget en dollars |
| Quota | commande `/usage` | non vérifié | Vérifie dans ta version (`/help`) ; sinon relève-le toi-même |
| Compactage | `/compact` | non vérifié | Vérifie dans ta version |

## Le moteur `copilot` du lanceur

`python outils/lancer_mission.py <id> --moteur copilot` construit une commande de la forme :

```
copilot -p "<brief + règles communes>" -s --no-ask-user [--model=<modèle>] [--add-dir=<dossier>]…
        [options détectées] --allow-tool=write --allow-tool=shell(git status) … --deny-tool=shell(git push) …
```

Au lancement réel, le lanceur lit d'abord l'aide de la version **qui sera lancée** : `copilot --no-auto-update --help`
(une commande locale, qui n'appelle aucun service). Si cette aide liste `--no-auto-update`, c'est elle qui fait foi et la
mission passe l'option ; sinon (option inconnue, erreur, aide vide), repli sur `copilot --help` et la mission **ne passe
pas** `--no-auto-update`. Pourquoi : deux versions installées côte à côte peuvent avoir des aides différentes, et une aide
lue sur l'une ne dit rien de l'autre. Le `--dry-run` écrit quelle aide a été lue. Les tests utilisent des textes d'aide
fictifs et un lecteur simulé.

### Options : dans l'aide, et utilisées par le lanceur

| Option | Dans l'aide / la documentation | Utilisée par le lanceur |
|---|---|---|
| `-p` / `--prompt`, `-s`, `--no-ask-user` | **Documenté** (référence programmatique) | **Oui**, toujours |
| `--model` | **Documenté** ; **observé** (CLI 1.0.98) : la valeur `auto` laisse Copilot choisir. Omettre `--model` est aussi accepté (code 0), mais l'équivalence avec `auto` n'est **pas établie** (non testé) | **Oui**, nom lu dans `copilot.modeles` (refus s'il est vide) ; `auto` seulement si l'aide de `--model` la documente, sinon refus clair |
| `--no-auto-update` | **Observé** dans l'aide d'une version du CLI | **Sous condition** : transmis si l'aide lue **avec** cette option la liste (voir « Versions multiples ») |
| `--add-dir`, `--allow-tool`, `--deny-tool` | **Documenté** | **Oui**, toujours (motifs non testés, voir plus bas) |
| `--output-format` (`text` ou `json`), `--resume` | **Documenté** | **Non** : sortie lue comme du texte brut ; pas de reprise de session |
| `--reasoning-effort` | **Observé** dans l'aide d'une version récente du CLI ; absent de la référence | **Sous condition** : seulement si ton aide la liste. Envoie l'effort du brief (`low`, `medium`, `high`) ; refuse une valeur que l'aide ne liste pas, si elle liste des valeurs |
| `--max-ai-credits` | **Observé** (même version) | **Sous condition** : seulement si l'aide la liste **et** si `copilot.credits_ia_max` est renseigné. Jamais déduit du budget USD |
| `--usage-output-file` | **Observé** (même version) | **Sous condition** : si l'aide la liste, vers `donnees/usage-<id>.json`, lu (voir « Fichier d'usage »), résumé dans le journal et le compte rendu, puis supprimé |
| `--allow-all-tools` | **Observé** : l'aide indique qu'il serait requis en mode non interactif. Son effet face à `--deny-tool` : **non testé** | **Sous condition** : jamais par défaut ; seulement si `copilot.autoriser_tous_outils` vaut `true` **et** que l'aide la liste |

Ici « observé » signifie : lu dans l'aide d'une version du CLI, sans plus. Aucune de ces options n'a été essayée dans une
mission réelle ; le lanceur ne les envoie que si ton aide les affiche, pour ne jamais faire échouer une commande sur
une option inconnue. `--dry-run` affiche les options détectées et celles qui seraient transmises.

### Réglages de `config.json` (clé `copilot`)

```json
"copilot": {
  "modeles": { "haiku": "…", "sonnet": "…", "opus": "…" },
  "credits_ia_max": null,
  "autoriser_tous_outils": false
}
```

- `modeles` : un nom par modèle de la grille, tel que ta version l'accepte (`/model` dans Copilot, ou l'aide du CLI),
  ou la valeur `"auto"`. Un nom **vide** pour le modèle demandé par le brief refuse la mission en nommant la clé à
  remplir (le lanceur n'envoie jamais de modèle « par défaut » à ta place) ; `"auto"` est un choix explicite, pas un
  vide.
- `credits_ia_max` : entier positif ou `null`. **Choix de conception** : le plafond de crédits IA est un réglage de
  config, pas un champ du brief. Le format du brief est commun aux deux moteurs et sa ligne « Exécution » parle en
  USD ; un second budget dans le brief invitait à convertir l'un en l'autre, ce que rien ne permet (un crédit IA n'est
  pas un dollar). Un plafond par installation est le plus simple ; un plafond par mission pourra venir plus tard.
- `autoriser_tous_outils` : voir [garde-fous.md](garde-fous.md#--allow-all-tools-avec-copilot). Par défaut `false`.

### Stratégie de modèle `auto`

Avec `copilot.modeles.<classe>` = `"auto"`, le lanceur passe `--model=auto` **seulement si** l'aide détectée de ton
CLI documente `auto` pour `--model` ; sinon il refuse en le disant (aide absente de `auto`, ou non lue). Le modèle
réellement utilisé n'est **jamais déduit** : c'est le champ `currentModel` du fichier d'usage s'il est présent ; sinon
le journal écrit « non relevé ». Le journal garde deux champs : `modele` (la classe demandée par le brief) et
`modele_reel`. Choix : un champ dédié et non la phrase `note`, parce qu'il se filtre et se compare sans analyse de
texte.

### Fichier d'usage

Format **observé sur une version du CLI, non garanti** : un JSON dont la racine porte `currentModel` (chaîne),
`totalPremiumRequestCost`, `totalUserRequests`, `totalNanoAiu`, `totalApiDurationMs` (nombres), `tokenDetails`
(`input`, `cache_read`, `cache_write`, `output`, chacun avec `tokenCount`) et `codeChanges` (`linesAdded`,
`linesRemoved`, `filesModifiedCount`), entre autres. Le lanceur applique une **liste blanche** : il ne reprend que
`currentModel`, `totalPremiumRequestCost`, `totalNanoAiu`, `totalUserRequests`, `totalApiDurationMs`, les jetons de
`tokenDetails` et les `codeChanges` numériques, quand ils sont présents et du bon type. Il tolère leur absence (et le
dit) et signale un champ de type inattendu au lieu de le deviner. **Rien d'autre n'est recopié** : pas de JSON brut,
même tronqué, ni dans le journal ni dans le compte rendu. Les autres clés de premier niveau sont seulement comptées
et nommées (« N champ(s) non reconnu(s), non repris : noms »), jamais leurs valeurs ; un fichier invalide est dit
« fichier d'usage illisible » avec le type de l'erreur, sans son contenu ; un fichier absent ou vide est dit tel quel.

### Application, enrobage PowerShell et versions multiples

- Sous PowerShell en **mode de langage restreint**, le script d'enrobage de `copilot` (un `.ps1`) a renvoyé une
  erreur `SetShouldExit` et un code de sortie peu fiable (**observé**). Préfère un exécutable `.exe` ou `.cmd` ;
  `python outils/capacites.py` signale un `copilot` résolu en `.ps1` et ne le lance pas.
- **Versions multiples** : `copilot --version` peut différer selon `--no-auto-update` (deux versions installées côte à
  côte, **observé**). Le lanceur transmet `--no-auto-update` quand l'aide lue avec cette option le liste : une mission
  est bornée dans le temps et son comportement (options, format d'usage) doit être celui de la version que tu as
  vérifiée, pas celui d'une mise à jour survenue entre deux lancements. L'aide et `--version` sont lues avec la même
  règle (d'abord avec l'option, repli sans elle), par le lanceur et par l'inventaire : ce qui est lu décrit la version
  réellement lancée.
- La priorité entre `--deny-tool` et `--allow-all-tools` est **non testée** (pas d'environnement isolé) :
  `autoriser_tous_outils` reste à `false` et n'est pas recommandé.

### Ce qui est non testé, ou non documenté

Le lanceur ne prétend rien garantir sur :

- le lancement réel d'une mission avec Copilot, de bout en bout ;
- la syntaxe exacte des motifs de `--deny-tool` (la documentation ne la détaille pas) et le fait qu'un refus l'emporte
  sur une autorisation, y compris sur `--allow-all-tools` ; les motifs `shell(git push)` et voisins sont ceux des
  exemples de la documentation ;
- la lecture du prompt sur l'entrée standard : non documentée, d'où un prompt passé en argument. Windows limite la ligne
  de commande à environ 32 000 caractères : le lanceur **refuse** un brief plus long ;
- la stabilité du format du fichier d'usage d'une version à l'autre (voir « Fichier d'usage ») ;
- le menu `/` dans l'application (**non testé**) ; la priorité de `--deny-tool` sur `--allow-all-tools` (**non testé**) ;
- une mission complète en sous-session sur un vrai projet (seul un projet fictif a été **observé**, sans les contrôles du lanceur) ;
- l'identifiant de session et les refus de permission : Copilot n'en fournit pas dans la sortie lue par le lanceur ; le
  journal et le compte rendu écrivent donc « refus de permission non relevés », jamais `0` ;
- la durée max : elle est appliquée par le lanceur lui-même (arrêt de l'arbre de processus), pas par Copilot.

Si une mission copilot échoue avec un message qui réclame `--allow-all-tools`, le lanceur s'arrête avec une
explication et **ne relance pas** : voir [garde-fous.md](garde-fous.md#--allow-all-tools-avec-copilot).

Comme `--output-format=json` produit du JSONL dont le format n'a pas été vérifié, le lanceur lit la sortie de `-s` comme
du texte brut : un code de retour différent de zéro vaut « échouée », sinon « terminée ».

## Première configuration

Pas à pas : [installation.md, « Configurer Copilot »](installation.md#3-bis-configurer-copilot).

## Essais à faire avant de s'y fier (45 minutes)

1. **Noyau** : l'essai de la section « Application seule » (question dont la réponse n'est que dans `AGENTS.md`).
2. **Skills** : l'exécution est observée dans l'application 1.5.0 ; reste à vérifier le menu `/`, comment un argument
   est transmis (`/note ajouter un export`) et si `creuser` apparaît en double.
3. **CLI** : `copilot --help`, puis `copilot -p "dis OK" -s`. Recopie ici les options réellement disponibles dans ta
   version.
4. **Interdits** : lance `copilot -p "exécute git push" --deny-tool="shell(git push)" -s` dans un dépôt de test **sans
   remote** et vérifie que la commande est bloquée.
5. **`--allow-all-tools` et `--deny-tool`** : seulement si tu envisages `autoriser_tous_outils: true`. Dans un dépôt de
   test sans remote, `copilot -p "exécute git push" --allow-all-tools --deny-tool="shell(git push)" -s` : la commande
   doit être bloquée. Sinon, laisse `false`.
6. **Effort** : `--dry-run`, puis une mission courte : vérifie que `--reasoning-effort=<effort du brief>` est accepté.
7. **Crédits IA** : renseigne `credits_ia_max` à une petite valeur, lance une mission de test et vérifie que la
   mission s'arrête quand le plafond est atteint (et ce que le CLI dit).
8. **Fichier d'usage** : après une mission, lis `Consommation Copilot` dans le compte rendu et compare avec ce que tu
   vois dans Copilot ; vérifie que les champs lus correspondent au fichier réel de ta version.
9. **Modèle** : renseigne `copilot.modeles` avec des noms que `/model` ou l'aide accepte, ou `auto` si l'aide le
   documente ; après une mission, vérifie que `modele_reel` du journal est `currentModel` du fichier d'usage.
10. **Mission** : `--moteur copilot --dry-run`, puis une mission de documentation de 5 minutes sur un dépôt de test.

Les résultats de ces essais sont à noter dans ce fichier : un « non testé » ne devient « testé » qu'après coup.

## Ce qui n'est pas fourni pour Copilot

Les agents personnalisés en lecture seule (mode 1), les hooks de blocage et les règles par dossier ne sont pas livrés
en v1. La commande `/conseil` dit, côté Copilot, de jouer les rôles l'un après l'autre si les sous-agents ne
sont pas disponibles ; ce ne sont alors pas des avis séparés, et elle le dit.
