@AGENTS.md

## Spécifique à Claude Code

- Les commandes `/configurer`, `/point`, `/quoi-faire`, `/note`, `/lancer`, `/go`, `/nouveau-projet` et `/conseil` sont dans
  `.claude/commands/`, la skill `creuser` dans `.claude/skills/creuser/`. Ces fichiers sont **générés** : on
  modifie la source dans `commandes/`, puis on lance `python outils/generer_commandes.py`.
- Mode 1 : un sous-agent en lecture seule (outil `Agent`, sans outils d'écriture).
- Mode 2 : `python outils/lancer_mission.py <id> --moteur claude`, qui lance `claude -p` dans le dossier du projet.
- Mode 3 : la session courante, où l'utilisateur répond aux demandes d'autorisation.
- Consommation : la commande `/usage` de Claude Code, si elle est disponible, donne les pourcentages ; sinon les
  demander à l'utilisateur.
- Compactage : `/compact` est tapé par l'utilisateur ; Polaris signale le moment et donne la commande.
