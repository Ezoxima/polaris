# Polaris avec GitHub Copilot

La documentation de Copilot évolue vite. Cette page distingue ce qui est **documenté** (avec le lien de la source,
consultée le 25 novembre 2026) de ce qui est **non testé** : rien de ce qui concerne Copilot n'a été exécuté lors de
la construction de ce dépôt, car Copilot CLI n'était pas installé sur le poste de développement. Une ligne marquée
« documenté » dit seulement que la documentation l'affirme, pas qu'elle a été essayée ici.

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

## Correspondance Claude Code et Copilot

| Brique de Polaris | Côté Claude Code | Côté Copilot | Statut |
|---|---|---|---|
| Noyau (rôle, aiguillage, garde-fous) | `CLAUDE.md`, qui importe `AGENTS.md` | `AGENTS.md` à la racine | **Documenté** : lu par Copilot CLI, par VS Code (Copilot Chat), par l'agent de code cloud et la revue de code. **Non testé** ici |
| Instructions propres à Copilot | — | `.github/copilot-instructions.md` | **Non fourni** : `AGENTS.md` suffit d'après la documentation. Ajoute-le seulement si ton environnement ne lit pas `AGENTS.md` |
| Règles par dossier | `CLAUDE.md` secondaires | `AGENTS.md` du dossier le plus proche (documenté) ou `.github/instructions/*.instructions.md` avec `applyTo` | **Documenté**, non utilisé par Polaris |
| Commandes (`/point`, `/lancer`…) | `.claude/commands/<nom>.md` | skills `.github/skills/<nom>/SKILL.md` | **Documenté** : le front matter exige `name` (identique au dossier) et `description` ; VS Code appelle une skill par `/nom`. **Non testé** : passage d'argument après le nom, affichage dans la liste des commandes |
| Skill `creuser` | `.claude/skills/creuser/SKILL.md` | `.github/skills/creuser/SKILL.md` | **Documenté**, **non testé**. La page GitHub dit que Copilot lit aussi `.claude/skills/` : la skill peut alors apparaître deux fois |
| Fichiers `.prompt.md` | — | non générés | **Documenté** : réservés aux sessions « Local » de VS Code, et ce mode est annoncé comme déprécié (retrait prévu en février 2027) ; la page recommande les skills |
| Mode 1 (sous-agent en lecture seule) | outil `Agent` | agent personnalisé `.github/agents/<nom>.agent.md` avec `tools` restreints | **Documenté** (emplacement, front matter). **Non fourni** en v1 |
| Mode 2 (mission sans fenêtre) | `claude -p` | `copilot -p` | Voir ci-dessous. **Non testé** |
| Mode 3 (session interactive) | session normale | session normale de Copilot | Sans objet |
| Modèle | `--model` | `--model=MODELE`, ou variable `COPILOT_MODEL` | **Documenté**. Les noms se déclarent dans `config.json` |
| Effort | `--effort` | aucune option de ligne de commande documentée | La clé de configuration `effortLevel` existe, mais le lanceur n'envoie rien |
| Budget | `--max-budget-usd` | aucune option documentée pour `copilot -p` | Le lanceur n'envoie rien ; seule la durée max est appliquée |
| Quota | commande `/usage` | non vérifié | Vérifie dans ta version (`/help`) ; sinon relève-le toi-même |
| Compactage | `/compact` | non vérifié | Vérifie dans ta version |

## Le moteur `copilot` du lanceur

`python outils/lancer_mission.py <id> --moteur copilot` construit une commande de la forme :

```
copilot -p "<brief + règles communes>" -s --no-ask-user [--model=<modèle>] [--add-dir=<dossier>]…
        --allow-tool=write --allow-tool=shell(git status) … --deny-tool=shell(git push) …
```

Options **documentées** dans la référence programmatique : `-p` / `--prompt`, `-s` (réponse seule, sans statistiques),
`--no-ask-user`, `--model`, `--add-dir`, `--allow-tool`, `--deny-tool`, `--output-format` (`text` ou `json`) et
`--resume`. Les outils se nomment `shell`, `write`, `read`, `url`, avec des motifs comme `shell(git:*)` ou
`shell(npm test)`.

Ce qui est **non testé**, ou **non documenté**, et que le lanceur ne prétend donc pas garantir :

- le lancement réel d'une mission avec Copilot, de bout en bout ;
- la syntaxe exacte des motifs de `--deny-tool` (la documentation ne la détaille pas) et le fait qu'un refus l'emporte
  sur une autorisation ; les motifs `shell(git push)` et voisins sont ceux des exemples de la documentation ;
- la lecture du prompt sur l'entrée standard : non documentée, d'où un prompt passé en argument. Windows limite la ligne
  de commande à environ 32 000 caractères : le lanceur **refuse** un brief plus long (le dire clairement vaut mieux
  qu'une troncature silencieuse) ;
- l'identifiant de session, le coût et les refus de permission : Copilot n'en fournit pas dans la sortie lue par le
  lanceur, qui journalise donc « coût non fourni » ;
- la durée max : elle est appliquée par le lanceur lui-même (arrêt de l'arbre de processus), pas par Copilot.

Comme `--output-format=json` produit du JSONL dont le format n'a pas été vérifié, le lanceur lit la sortie de `-s` comme
du texte brut : un code de retour différent de zéro vaut « échouée », sinon « terminée ».

## Essais à faire avant de s'y fier (30 minutes)

1. **Noyau** : ouvre le dépôt dans Copilot, demande « Quel est ton rôle ? Que t'interdis-tu ? Où est le registre ? » ;
   la réponse doit reprendre `AGENTS.md`. Sinon, ajoute `.github/copilot-instructions.md` qui renvoie vers `AGENTS.md`.
2. **Skills** : vérifie que `/point` et `/note` sont proposées, et comment un argument est transmis
   (`/note ajouter un export`). Vérifie si `creuser` apparaît en double.
3. **CLI** : `copilot --help`, puis `copilot -p "dis OK" -s`. Recopie ici les options réellement disponibles dans ta
   version.
4. **Interdits** : lance `copilot -p "exécute git push" --deny-tool="shell(git push)" -s` dans un dépôt de test **sans
   remote** et vérifie que la commande est bloquée.
5. **Modèle** : renseigne `copilot.modeles` dans `config.json` avec des noms que `copilot --help` ou `/model` accepte.
6. **Mission** : lance `--moteur copilot --dry-run`, puis une mission de documentation de 5 minutes sur un dépôt de test.

Les résultats de ces essais sont à noter dans ce fichier : un « non testé » ne devient « testé » qu'après coup.

## Ce qui n'est pas fourni pour Copilot

Les agents personnalisés en lecture seule (mode 1), les hooks de blocage et les règles par dossier ne sont pas livrés
en v1. La commande `/conseil` dit, côté Copilot, de jouer les quatre rôles l'un après l'autre si les sous-agents ne
sont pas disponibles : l'indépendance des avis est alors réduite.
