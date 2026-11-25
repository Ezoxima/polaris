---
description: "Conseil d'avis contradictoires sur un cadrage (MVP, périmètre, décision), sur demande seulement"
argument-hint: "<carte, fichier de cadrage ou sujet>"
---
<!-- Fichier généré par outils/generer_commandes.py à partir de commandes/conseil.md : ne pas modifier à la main. -->

Sujet : `$ARGUMENTS` (si c'est vide, demande-le). Tu es l'orchestrateur : **tu n'écris pas de code**, tu réunis un
conseil d'avis, puis tu synthétises.

## Périmètre (refuser sinon, en le disant)
- **Cadrage uniquement** : MVP, périmètre, découpage, choix de principe, décision d'architecture. Pas de code, pas
  de revue de diff, pas de question simple (une réponse directe suffit).
- **Sur ma demande seulement** : ne propose jamais le conseil de toi-même, ne le lance jamais seul.
- Un sujet qui touche l'argent réel ou la production reste possible (le conseil ne fait que réfléchir), mais rappelle
  que l'exécution passera en mode 3.

## 1. Préparer le dossier
Rassemble **une seule base commune** que les membres liront : l'échange de cadrage (fichier ou carte indiqués,
ou le résumé que je colle), la fiche du projet dans `registre/projets.md` (ou sa version `.local.md`, voir AGENTS.md), les règles du `AGENTS.md` ou du
`CLAUDE.md` du projet. Cite des **chemins**, ne recopie pas de gros blocs ; aucun secret. Si le dossier est trop mince
pour juger, dis ce qui manque et propose de le compléter avec la skill `creuser`, mode `dossier` (trois tours au
plus) ; après mon « ok » sur son récapitulatif, ajoute-le au dossier. Si je refuse, arrête-toi.
Formule la **question à trancher** en une ou deux phrases (par exemple « Quel MVP minimal pour l'application, et
que repousse-t-on ? »). Si une bibliothèque de méthodes est configurée (`registre/nova.md` ou sa version `.local.md`, voir AGENTS.md), choisis 0 à 2 fichiers
utiles et cite-les aux membres.

## 2. Récapitulatif et accord
Affiche : le sujet, la question, les rôles proposés (quatre par défaut, ajustables), deux tours, la classe de modèle
standard avec un effort élevé pour les membres, et le **plan d'exécution** : combien d'agents ou de passes tu
comptes lancer. Ne garantis rien sur le coût : donne seulement un ordre de grandeur, présenté comme une estimation
non vérifiée (relève la consommation actuelle si la plateforme l'expose). **Attends mon accord explicite : aucun agent
n'est lancé avant.**

## 3. Tour 1 : un avis par rôle (en parallèle si la plateforme le permet)
Un seul message, un appel de l'outil `Agent` par rôle (`subagent_type: Plan`, `model: sonnet`, lecture seule).
Chaque membre reçoit le dossier, la question et **son rôle seul**. Ne promets pas que les avis soient indépendants :
ils viennent du même modèle, avec la même base. Les rôles :
1. **Le Pragmatique** : le plus petit MVP qui apporte de la valeur ; ce qu'on coupe, ce qui attend la v2.
2. **L'Avocat du diable** : les hypothèses fragiles, ce qui fait échouer le projet, ce que le dossier suppose sans
   l'avoir vérifié.
3. **Le Gardien des risques** : réversibilité, argent, données, sécurité, règles du projet et garde-fous ; ce qu'il
   ne faut pas automatiser.
4. **Le Comptable** : coût réel (quota, temps), complexité, maintenance, dépendances ; l'option la moins chère qui tient.

Consigne commune : réponse de **300 mots au plus**, une recommandation nette, trois points d'appui précis (cités dans
le dossier), une chose qu'il ignore. Pas de politesse, pas de reformulation de la question.

## 4. Tour 2 : critique croisée
Chaque membre reçoit les **trois autres avis, anonymisés (A, B, C)**, et doit désigner la faille la plus grave d'un
avis, puis dire s'il change d'opinion et pourquoi. **150 mots au plus.** Un membre qui ne change pas d'avis le dit :
ne force pas le consensus.

## 5. Synthèse (toi)
Après mon accord (ne réserve pas d'identifiant ni n'écris de fichier avant), écris dans
`briefs/conseil-AAAAMMJJ-NN-xxxx.md` (identifiant réservé par `python outils/nouvel_id.py`, un fichier court) ; sans
accord, donne la synthèse dans la conversation seulement :
- **Question** et dossier utilisé (chemins).
- **Recommandation** : le MVP ou la décision proposée, en quelques lignes.
- **Accords solides** (trois membres sur quatre au moins) et **désaccords restants**, **sans les lisser** : qui pense
  quoi, et l'enjeu de la décision.
- **Ce qu'on repousse** (hors MVP) et **ce qu'il faut vérifier avant de s'engager**.
- **Ma décision à prendre** : les un à trois choix qui sont les miens.

Rappelle que des avis du même modèle partagent des angles morts : un accord unanime n'est pas une preuve.

## 6. Clôture
Donne la synthèse en quelques lignes et le chemin du fichier. **Ne modifie rien d'autre** : propose seulement de
reporter le résultat sur la carte (description ou prochaine étape) ou de créer des cartes, après mon « ok ». Ne
lance aucune mission.
