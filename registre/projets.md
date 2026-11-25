# Registre des projets

Une fiche par projet. **Secrets : noms seulement, jamais de valeur.** Les deux fiches ci-dessous sont des
exemples fictifs : remplace-les par tes projets (ou laisse `/nouveau-projet` les créer).

Racine des projets : `~/projets` (à adapter ; les chemins réels vivent dans `config.json`, clé `projets`).

## Mots-clés → projet

| Mot-clé | Projet |
|---|---|
| boutique, panier, commande, paiement test | `boutique-web` |
| import, nettoyage, tables, planification, pipeline | `pipeline-ventes` |

Un mot qui apparaît dans deux projets (« export », « token ») ne fait jamais deviner : Polaris demande.
Chaque erreur d'aiguillage ajoute le mot manquant à la fiche concernée.

## Modèle de fiche

```markdown
## <nom-du-projet> — <famille> — <Actif | En pause | Fini | À supprimer>
- Chemin : `<chemin local>` · branche `<main>` · remote `<url ou « aucun »>`
- Phase : <POC | MVP | Produit final>
- Stack : <langage, base, outils> ; tests : `<commande>` ; lint : `<commande>`
- Porte d'entrée : `AGENTS.md` ou `CLAUDE.md` du dépôt + `memoire/INDEX.md`
- Mots-clés : <5 à 10 mots qui permettent de reconnaître ce projet dans une phrase>
- Variantes : <facultatif : liste des variantes, ex. clients ou environnements ; « sans objet » sinon>
- Règles sensibles : <données clients, production, ce qu'aucune mission ne doit toucher>
- Tâches planifiées : <noms exacts et cadence, ou « aucune »>
- Secrets utilisés : <NOMS seulement>
```

Quand le projet a des variantes, ajoute une **matrice capacité × variante** (✅ fait · 🟡 partiel · ⬜ absent ·
➖ sans objet) : c'est la carte des réplications possibles.

---

## boutique-web — Applications — Actif
- Chemin : `~/projets/boutique-web` · branche `main` · remote `aucun`
- Phase : MVP
- Stack : Python, FastAPI, PostgreSQL ; tests : `python -m pytest` ; lint : `ruff check`
- Porte d'entrée : `CLAUDE.md` du dépôt + `memoire/INDEX.md`
- Mots-clés : boutique, panier, commande, catalogue, paiement test
- Variantes : une par pays (FR, DE) ; la mission d'une variante ne touche pas aux autres.
- Règles sensibles : aucune écriture dans la base de production ; le paiement ne se teste qu'avec les clés de test
  du prestataire.
- Tâches planifiées : aucune
- Secrets utilisés : `PAIEMENT_CLE_TEST`, `DATABASE_URL`

| Capacité | FR | DE |
|---|---|---|
| Catalogue | ✅ | 🟡 |
| Panier | ✅ | ⬜ |
| Paiement test | 🟡 | ⬜ |

## pipeline-ventes — Données — Actif
- Chemin : `~/projets/pipeline-ventes` · branche `main` · remote `aucun`
- Phase : POC
- Stack : Python, pandas, SQLite ; tests : `python -m pytest` ; lint : `ruff check`
- Porte d'entrée : `AGENTS.md` du dépôt + `memoire/INDEX.md`
- Mots-clés : import, nettoyage, ventes, planification, pipeline
- Variantes : sans objet
- Règles sensibles : les exports clients ne quittent pas le poste ; pas de suppression des sauvegardes `.db`.
- Tâches planifiées : `pipeline-ventes-nuit` (chaque nuit à 02:00)
- Secrets utilisés : aucun
