# Grille modèle / effort

**Règle : avec le modèle de raisonnement fort, l'effort ne dépasse jamais `high`.** Pas de plafond pour les autres
classes. Ce plafond est appliqué par le lanceur (`outils/lancer_mission.py`). C'est un point de départ, ajusté à
l'usage avec les mesures du journal (`donnees/missions.jsonl`). Polaris annonce le couple choisi avant de lancer ;
l'utilisateur peut le changer.

## Classes de modèle

| Classe | Rôle | Claude Code (`--model`) | Copilot CLI |
|---|---|---|---|
| léger | traduction, résumés, tri, veille | `haiku` | un modèle léger de ta liste |
| standard | code, documentation, petits correctifs | `sonnet` | un modèle standard de ta liste |
| fort | diagnostic, architecture, cadrage | `opus` | un modèle de raisonnement fort de ta liste |

Les noms de modèles changent vite. Pour Copilot, ils se déclarent dans `config.json` (clé `copilot.modeles`) ; sans
déclaration, le lanceur n'envoie pas `--model` et Copilot utilise son modèle par défaut.

## Grille

| Type de tâche | Classe | Effort | Durée max (mode 2) |
|---|---|---|---|
| Traduction, résumés, `/point`, veille | léger | `low` | 5 min |
| Ménage, documentation, petits correctifs | standard | `medium` | 20 min |
| Chantier de code | standard | `high` | 90 min |
| Diagnostic difficile, architecture | fort | `medium`, puis `high` si nécessaire | 60 min |
| Cadrage d'un nouveau projet, décision structurante | fort | `high` | mode 3 uniquement |

- **Le code s'écrit avec la classe standard**, jamais avec la plus chère : à durée égale, le modèle fort coûte
  plusieurs fois plus. Il est réservé à ce qu'un modèle standard ne tranche pas bien.
- Une tâche trop grosse n'est jamais confiée d'un bloc : on la découpe en missions de 20 à 90 minutes.
- Durée max atteinte : la session est arrêtée, après avoir laissé un compte rendu (ce qui a été essayé, ce qui
  bloque, la proposition).
- **Copilot CLI** : aucune option d'effort ni de budget n'est documentée pour `copilot -p` (voir
  [../docs/copilot.md](../docs/copilot.md)). La durée max reste appliquée par le lanceur ; l'effort et le budget
  du brief sont alors ignorés, et le lanceur le signale.

## Consommation estimée

Elle se mesure en **% de la fenêtre courte** (par exemple 5 heures) et en **% de la limite hebdomadaire** quand la
plateforme les affiche, sinon dans l'unité qu'elle affiche (requêtes premium, crédits). Jamais en jetons : ce n'est
pas ce que l'utilisateur voit.

**Le tableau est vide au départ, volontairement.** Ne rien inventer : le remplir avec les mesures avant/après
inscrites au journal. Les premières estimations sont souvent surévaluées d'un facteur deux ou trois ; la
calibration se fait après quelques missions de chaque type.

| Type de mission × classe | % fenêtre courte | % hebdo | Mesures |
|---|---|---|---|
| Documentation, standard `medium` | à mesurer | à mesurer | 0 |
| Chantier de code, standard `high` | à mesurer | à mesurer | 0 |
| Diagnostic, fort `high` | à mesurer | à mesurer | 0 |
| Résumé, léger `low` | à mesurer | à mesurer | 0 |

Repères de calibration, à confirmer chez toi : une mission bien balisée (fichiers cités, critère de fin, périmètre)
coûte peu et dure moins d'une demi-heure ; la consommation vient surtout du **contexte de la session de Polaris**,
relu à chaque échange. Avant de lancer une chaîne de missions, compacter ou ouvrir une session neuve.
