# Modèle : `CADRAGE.md` d'un nouveau projet

Utilisé par `/nouveau-projet`. Principe : donner à l'agent ce qu'il ne doit pas deviner, sans figer ce qui n'est pas
encore décidé.

Règles de remplissage :

- **Un seul fichier** à la racine du dépôt, **80 à 120 lignes** au plus en phase POC. Il grossit avec le projet,
  pas avant.
- **Rien n'est obligatoire sauf le besoin.** Une section qui ne s'applique pas vaut « Sans objet (raison) » :
  l'agent sait alors que ce n'est pas un oubli.
- **Trois états possibles pour chaque choix** : *Décidé* (l'agent s'y tient), *À proposer* (l'agent propose deux
  ou trois options argumentées, l'utilisateur tranche, puis on passe en *Décidé*), *Ouvert* (on en reparle plus
  tard ; l'agent ne choisit pas seul).
- Aucun secret, aucune donnée personnelle réelle (noms de secrets seulement).
- Le `AGENTS.md` ou le `CLAUDE.md` du dépôt renvoie à ce fichier ; il ne le recopie pas.

Types de projet (choisis au cadrage, ils décident quelles sections comptent) :

| Type | §3 Fonctionnement | §4 Interface | §5 Données |
|---|---|---|---|
| Application (web, mobile, bureau) | écrans et parcours | oui | oui |
| Script, pipeline, automatisation | entrées, traitements, sorties | souvent sans objet | selon le cas |
| Modélisation de données (schéma, entrepôt) | sans objet, ou règles de gestion | sans objet | **cœur du projet** |
| Analyse, tableau de bord, rapport | questions posées, sources, livrable | oui (lisibilité) | sources et indicateurs |
| Autre | à préciser | à préciser | à préciser |

---

```markdown
# Cadrage — <nom du projet>

Type : <Application | Script/pipeline | Modélisation de données | Analyse/tableau de bord | Autre>
Phase actuelle : POC · Cadré le JJ/MM/AAAA · Mis à jour le JJ/MM/AAAA

## 1. Besoin et phases
- **Problème et public** : <une phrase : quel problème, pour qui>
- **Mesure du succès** : <un chiffre ou un constat observable>

| Phase | Ce qu'on prouve ou livre | Critère de sortie (vérifiable) | Hors phase |
|---|---|---|---|
| POC | <la question technique ou métier à trancher> | <« X fonctionne quand… »> | <…> |
| MVP | <le plus petit produit réellement utilisable> | <…> | <…> |
| Livrable | <la version qu'on garde ou qu'on donne> | <…> | <…> |

<Si la logique POC, MVP, Livrable ne s'applique pas (une étude ponctuelle), le dire en une ligne et garder une seule
ligne « Livrable ». Les phases suivantes peuvent rester *Ouvert* : seul le POC doit être complet.>

- **Exigences du POC** : <3 à 6 puces, chacune testable>

## 2. Choix techniques
| Sujet | État | Choix ou options |
|---|---|---|
| Langage / framework | Décidé · À proposer · Ouvert | <…> |
| Base de données | … | <…> |
| Exécution (local, planifié, hébergé) | … | <…> |
| Dépendances clés | … | <…> |

- **Commandes** (quand décidées) : installer `<…>` · lancer `<…>` · tester `<…>` · lint `<…>`
- **Contraintes** : <ce que l'agent ne doit pas faire seul : service payant, nouveau framework, autre base…>

## 3. Fonctionnement
<Selon le type : écrans dans l'ordre (application) ; entrées, traitements, sorties et fréquence (pipeline) ;
règles de gestion clés (modélisation) ; questions posées, sources, livrable attendu (analyse).>

## 4. Interface
<Si interface : thème clair ou sombre, ambiance, palette et typographie (contraste AA au minimum), composants
réutilisés, densité. Sinon : « Sans objet (pas d'interface) ».>

## 5. Données
<Entités ou tables principales : nom, attributs clés (type), identifiants, relations et cardinalités. Données
sensibles signalées. Pour un projet de modélisation, cette section est le livrable.>

## 6. Plan de réalisation
<2 à 4 étapes du POC = les cartes du premier lot, dans l'ordre, chacune avec son « fini quand ». La première est
toujours la plus petite chose qui tourne (ou qui se vérifie) de bout en bout.>
```
