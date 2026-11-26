---
description: "Prépare le brief d'une carte, choisit modèle et effort, affiche la consommation et lance la mission"
argument-hint: "<titre ou mot-clé de la carte>"
---
<!-- Fichier généré par outils/generer_commandes.py à partir de commandes/lancer.md : ne pas modifier à la main. -->

Carte : `$ARGUMENTS`. Tu es l'orchestrateur : **tu n'écris pas de code dans les projets**, tu prépares et lances une
mission.

## 1. Vérifier (refuser sinon, en le disant)
**Kanban d'abord** : lis `kanban.mode` dans `config.json` avant toute lecture ou écriture d'Orion. `github` : retrouve la carte par `gh` (recettes de `registre/kanban.md`). `manuel` : aucune lecture d'Orion : demande-moi le titre, la description, la colonne et la prochaine étape de la carte tenue dans mon outil, puis dis-moi à la fin quoi y modifier. `aucun` : pas de carte : le brief se rédige d'après ce que je te dis, et l'étape « carte » est sautée et annoncée. Clé absente : traite comme `github` (compatibilité) et dis-le en une ligne.
- Retrouve la carte (`registre/kanban.md` ou sa version `.local.md`, voir AGENTS.md) et **lis sa description** (`content.body` dans la sortie de
  `gh project item-list`) en plus des champs. Plusieurs candidates : demande laquelle. Description vide : dis-le,
  rédige-la d'après la carte et le registre, et propose de l'enregistrer (`item-edit --body`) avant de lancer.
- **Refus** si : carte hors « Prêt » et « En cours » (« À cadrer »
  se cadre d'abord) · nature POC (jamais lancé directement) · taille L ou XL sans découpage (propose la première
  mission) · une mission est déjà en cours sur **ce projet** (un autre projet ne bloque pas).
- **Mode 3 obligatoire** (jamais de lancement sans fenêtre) si la carte, y compris sa section « Garde-fous »,
  touche : l'argent réel, un `git push`, une commande administrateur, un mot de passe ou un code de validation,
  une base de production, une suppression de données, une tâche planifiée, une réécriture d'historique git ou une
  installation. Dis-le et prépare seulement le brief pour une session interactive.
- Une seule variante par mission.

## 2. Rédiger le brief
Format exact de `registre/mission.md` (ou sa version `.local.md`, voir AGENTS.md), gabarit `modeles/brief.md`. Pars de la description de la carte : son
« Contexte » alimente le contexte du brief, son « Objectif / fait quand » le critère de fin, ses « Pointeurs » la
liste de fichiers à lire (chemins cités, pas copiés), ses « Garde-fous » les interdits. La description peut dater :
en cas de désaccord, la **prochaine étape** et ce que je viens de te dire priment, et tu le signales. Lis la fiche
du projet dans `registre/projets.md` (ou sa version `.local.md`, voir AGENTS.md) (chemin, règles sensibles, porte d'entrée) ; ne lis pas les plans de reprise
entiers, la mission le fait. Si une bibliothèque de méthodes est configurée (`registre/nova.md` ou sa version `.local.md`, voir AGENTS.md), choisis 0 à 2
fichiers et cite leur chemin après avoir vérifié qu'ils existent. Aucun secret recopié. Réserve d'abord
l'identifiant avec `python outils/nouvel_id.py` (jamais de numéro deviné à la main), puis écris le brief dans
`briefs/<id>.md`.

## 3. Choisir modèle et effort (`registre/grille.md` ou sa version `.local.md`, voir AGENTS.md)
Le code se confie à la classe standard (effort élevé pour un chantier, moyen pour un ménage), jamais à la classe
forte, réservée au diagnostic, à l'architecture et au cadrage (effort `high` au plus). Le léger sert aux
traductions et aux résumés. Durée max selon la grille.

## 4. Voie, récapitulatif et accord
Lance `python outils/capacites.py --voie` (local, n'écrit rien) : il propose une voie d'après les capacités du poste et
ma préférence. **Propose-la, ne l'impose pas.** Une voie autre que `cli` (`sous_session`, `prompt`) passe par
`python outils/lancer_mission.py <id> --prompt --voie <prompt|sous_session> [--moteur …]`, qui écrit un prompt
autonome et ne lance rien ; dis quels contrôles elle ne garantit pas (verrou par projet, durée max, journal
automatique, permissions, relevé de consommation, arrêt d'urgence) : elle n'est jamais équivalente au lanceur.
Affiche : voie proposée et contrôles absents, projet, carte, variante, modèle, effort, mode, durée max, permissions
anticipées, **consommation estimée** (grille ; avertis si elle dépasse ce qui reste) et **ce qui sera écrit** : voie
`cli`, le journal (`lancee`…) et le compte rendu ; voie `prompt` ou `sous_session`, `briefs/<id>-prompt.md` et la ligne
`preparee` au journal (rien n'est lancé).
Consommation : si la plateforme ne permet aucune estimation (aucun relevé, grille sans mesure), écris **« estimation
indisponible »** avec l'unité de la plateforme si tu la connais (crédits IA, requêtes premium), et demande mon accord
quand même ; n'invente aucun chiffre. Relève la consommation actuelle avec l'outil de la plateforme s'il en existe un,
sinon demande-la-moi : ce sont les « avant ». **Attends mon accord explicite** avant toute écriture ou lancement ; je
peux changer le couple choisi.

## 5. Lancer (mode 2, voie acceptée)
- Dry-run d'abord, selon la voie. `cli` : `python outils/lancer_mission.py <id> --dry-run` (affiche le plan, exige le
  CLI du moteur). `prompt` / `sous_session` : `python outils/lancer_mission.py <id> --prompt --voie <voie> --dry-run`
  (n'écrit rien, n'exige aucun CLI). Il refuse proprement si une condition manque. Puis, après mon accord : voie `cli`,
  `python outils/lancer_mission.py <id> --moteur <claude|copilot>` ; autre voie, la même commande `--prompt` sans
  `--dry-run`. Jamais d'option qui contourne les permissions.
- Le lanceur écrit `lancee` puis `terminee`, `echouee` ou `arretee` au journal et le compte rendu dans
  `briefs/<id>-compte-rendu.md`. Il ne déplace aucune carte : fais-le à la fin.
- À la fin, **ne crois pas le compte rendu** : relance les tests et le lint du projet, relis `git status`, `git log`
  et `git diff --stat` (aucune référence distante changée, aucun fichier hors périmètre).
- Mets la carte à jour selon `kanban.mode` (voir section 1) : colonne, « prochaine étape », consommation mesurée,
  description corrigée si la mission l'a rendue fausse (`manuel` : dis-moi quoi changer dans mon outil ; `aucun` :
  saute-le). Ajoute la ligne `mesure` au journal avec les pourcentages d'après.
- Permission manquante ou échec : **arrête-toi et explique, ne change jamais de voie de ta propre initiative**. Propose (a) de l'accorder pour cette mission seulement, (b) le mode 3, (c) de redécouper ;
  je tranche.
- Si le chantier avait une variante et qu'il est clos : propose la carte « Répliquer dans <autre variante> »
  (À cadrer), dont le brief pointe vers l'implémentation de référence.
