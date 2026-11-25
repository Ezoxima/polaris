---
name: "nouveau-projet"
description: "Entretien de cadrage d'un nouveau projet, puis dossier, mémoire, fiche du registre et cartes Orion (phase POC)"
argument-hint: "<nom ou idée du projet, facultatif>"
---
<!-- Fichier généré par outils/generer_commandes.py à partir de commandes/nouveau-projet.md : ne pas modifier à la main. -->

Idée : le texte que j'écris après le nom de la commande (si c'est vide, demande-la). Mode 3 : tu es dans une session avec moi, avec la classe de modèle
**forte** et un effort `high` au plus (`registre/grille.md` ou sa version `.local.md`, voir AGENTS.md), jamais en mission automatique. Tu cadres, tu n'écris
pas de code applicatif : seulement les fichiers de cadrage ci-dessous.

## 1. Entretien (skill `creuser`, mode `complet`)
Mène l'entretien avec la skill `creuser` : le nombre de questions par tour est celui de `registre/preferences.md` (ou sa version `.local.md`, voir AGENTS.md)
(une seule par défaut), avec une recommandation par question, les faits cherchés par toi. Les dix thèmes ci-dessous sont la **liste de contrôle** à couvrir avant de clore, pas un
script : l'arbre de décisions fixe l'ordre (le type de projet ouvre les branches suivantes). Ne pose que ce que tu
ne peux pas déduire. Un mot ambigu : demande, ne devine pas.
1. **But et type** : quel problème, pour qui, en une phrase ; type de projet (application, script ou pipeline,
   modélisation de données, analyse ou tableau de bord, autre — voir `registre/cadrage.md` (ou sa version `.local.md`, voir AGENTS.md).
2. **Phases POC, MVP, Livrable** : pour le POC, ce qui montrerait que ça marche (critère de sortie vérifiable) et
   ce qui est hors POC ; pour le MVP et le Livrable, ce qui est déjà connu (le reste reste « Ouvert »). Si la
   logique ne s'applique pas, une seule ligne « Livrable ».
3. **Projet et variantes** : nom du projet (minuscules, tirets) ; le projet a-t-il des variantes (clients,
   environnements, plateformes) ? Une seule par chantier.
4. **Choix techniques** : pour chaque sujet (langage, base, exécution, dépendances), je peux répondre *décidé*,
   *aiguille-moi* ou *plus tard*. Sur *aiguille-moi* : propose deux ou trois options (forces, limites, coût, effort,
   cohérence avec mes autres projets du registre), recommande, et attends mon choix. Note aussi ce que l'agent ne
   doit pas choisir seul.
5. **Fonctionnement et interface** (seulement si le type s'y prête) : écrans et parcours pour une application,
   entrées et sorties pour un script, règles de gestion pour une modélisation ; pour une interface, l'ambiance
   souhaitée ou *aiguille-moi* (deux directions proposées).
6. **Données** : entités ou tables principales, attributs clés, relations, données sensibles.
7. **Sensible** : argent réel, données personnelles, base de production, tâches planifiées, droits
   administrateur. Chaque point devient une règle du `AGENTS.md` du projet et, si besoin, une carte de mode 3.
8. **Secrets** : leurs noms seulement, jamais une valeur.
9. **Mots-clés de reconnaissance** (5 à 10) pour l'aiguillage.
10. **Premier lot** : 2 à 4 chantiers possibles pour le POC, chacun avec son « fini quand ».

Les réponses 1, 2, 4, 5, 6 et 10 remplissent les six sections de `CADRAGE.md` (modèle : `registre/cadrage.md`).
Saute les questions que le type rend sans objet ; une section qui ne s'applique pas vaut « Sans objet (raison) ».
Chaque choix porte un état : Décidé, À proposer ou Ouvert — ne transforme jamais un « plus tard » en décision.

Si le projet ressemble à une brique qui existe déjà dans un autre dépôt (`registre/projets.md` ou sa version `.local.md`, voir AGENTS.md), dis-le avant de
repartir de zéro.

## 2. Récapitulatif et accord (rien n'est créé avant mon « ok »)
Montre : le dossier prévu (sous la racine des projets de `config.json`), la phase **POC**, les règles sensibles, la
liste exacte des fichiers et des cartes que tu vas créer. Vérifie que le dossier n'existe pas déjà ; s'il existe,
arrête et demande.

## 3. Créer, dans cet ordre
Chaque étape marquée « accord » est un acte distinct : demande mon « ok » pour elle seule (un « ok » sur le
récapitulatif ne couvre pas `git init`, le commit ni l'inscription au Kanban) et saute-la si je refuse. Un dossier
**sans Git** est un choix valide : les étapes suivantes marchent sans dépôt.
1. Le dossier du projet (accord : celui du récapitulatif).
2. `git init` (accord séparé, sautable) ; puis le premier commit **local** (accord séparé, sautable ; jamais de
   `git push`, jamais de dépôt distant sans que je le demande, et alors toujours privé).
3. `CADRAGE.md` à la racine, d'après `registre/cadrage.md` : type, puis les six sections, 80 à 120 lignes au plus.
4. `AGENTS.md` du dépôt, 60 à 80 lignes au plus : but, phase POC et critère de sortie, stack et commandes, règles
   sensibles, secrets (noms), conventions de travail (langue, tests avant de conclure), renvoi vers `CADRAGE.md`
   (« lire avant toute nouvelle fonctionnalité ; le mettre à jour quand un choix change ») et vers
   `memoire/INDEX.md`. Pas de recopie du cadrage.
5. `memoire/INDEX.md` (une ligne par axe) et `memoire/<axe>.md` (gabarit `modeles/memoire-axe.md`), dont le premier
   « État au JJ/MM » est le cadrage.
6. `registre/projets.md` : la fiche au format du modèle, **Phase : POC** ; `memoire/INDEX.md` de Polaris : une ligne.
   Ajoute aussi le projet à `config.json` (clé `projets`) pour que le lanceur le connaisse : montre-moi la ligne.
7. Inscription au Kanban (accord séparé, sautable ; seulement si Orion est le système de suivi choisi : ne crée
   pas un second tableau à côté d'un Kanban existant) : **montre** d'abord la liste des cartes (une carte « Cadrer le POC de <nom> » de nature POC en « À
   cadrer », plus les deux à quatre cartes du premier lot, avec projet, taille, nature, prochaine étape et
   **description** selon le modèle de `registre/kanban.md` (ou sa version `.local.md`, voir AGENTS.md), puis crée-les après mon accord, chacune avec `--body`.
   Un POC ne se lance jamais directement.
8. Une ligne au journal des missions (mode 3, accord séparé : c'est une écriture dans `donnees/`) et un récapitulatif : ce qui a été créé, ce qui reste à décider, la
   prochaine commande utile (`/lancer`, `/quoi-faire`).

## Garde-fous
Aucun secret recopié · aucune installation · rien d'écrit hors du nouveau projet et de Polaris · pas de tâche
planifiée · pas de `git push` · le `AGENTS.md` du nouveau projet prime ensuite sur celui de Polaris pour ses règles.
