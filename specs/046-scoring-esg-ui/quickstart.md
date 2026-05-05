# Quickstart — F46 Scoring ESG visualisations UI

**Date** : 2026-05-04

Procédure pas-à-pas pour démarrer la stack et valider la feature `/scoring` localement de bout en bout.

## 1. Prérequis

- Postgres 16 + pgvector lancé via `make db-up` (port 5432).
- Migrations appliquées : `make migrate` (`alembic upgrade head`).
- Backend démarré : `make backend` (port 8010).
- Frontend démarré : `make frontend` (port 3001).
- Compte PME de test créé via le seed F02 (ou via `/register` puis `/login`).
- Catalogue F09 publié avec au moins les référentiels `BOAD`, `CDP`, `GRI` (seed F09 par défaut suffit).

## 2. Préparer un état initial

Depuis le frontend authentifié, saisir un profil entreprise minimal qui déclenche le `VALUE_SOURCE_MAP` :

1. Aller sur `/profil-entreprise` (F11) → renseigner :
   - Effectifs : `120`
   - Chiffre d'affaires : `5 000 000 XOF`
   - Pays du siège : `CI`
   - Gouvernance : `board_independence = true`, `audit_interne = false`
   - Pratiques : `politique_rse = true`, `bilan_carbone = false`
2. Sauvegarder.

## 3. Calculer un premier score

Option A (depuis la page `/scoring`) :

1. Naviguer vers `/scoring` ; un état vide s'affiche pour le référentiel par défaut `BOAD`.
2. Cliquer « Lancez votre premier diagnostic » → spinner → score affiché.

Option B (curl pour seeding e2e) :

```bash
TOKEN="<jwt PME>"
ME_ID="<entreprise_id>"

curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8010/me/scoring/entreprise/$ME_ID/recompute?referentiel=BOAD"
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8010/me/scoring/entreprise/$ME_ID/recompute?referentiel=CDP"
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8010/me/scoring/entreprise/$ME_ID/recompute?referentiel=GRI"
```

## 4. Vérifier la page `/scoring` (US1, US2, US3)

1. Ouvrir `/scoring` (le référentiel par défaut `BOAD` est sélectionné, l'URL devient `/scoring/BOAD`).
2. Vérifier la présence du score global, du radar E/S/G, du % de couverture, de la date du dernier calcul, de la version du référentiel.
3. Cliquer l'onglet `CDP` → URL `/scoring/CDP`, données mises à jour < 200 ms (cache hit après deuxième visite).
4. Cliquer « Comparer » → drawer/modal s'ouvre, sélectionner `BOAD` et `CDP` → barres horizontales côte à côte par pilier.

## 5. Drilldown et drawer indicateur (US4)

1. Sur `/scoring/BOAD`, dérouler l'accordéon **Environnement**.
2. Cliquer sur la ligne d'un indicateur **éditable** (par exemple `EFFECTIFS_TOTAL` ou un autre présent dans `VALUE_SOURCE_MAP`).
3. Drawer s'ouvre à droite : nom, définition, valeur, unité, formule, sources, graphique linéaire (vide si un seul calcul existe — c'est OK).
4. Cliquer « Modifier » → bottom sheet `ask_number` avec valeur courante.
5. Saisir une nouvelle valeur valide → soumettre → le drawer se met à jour, le score global et le radar de la page changent sans rechargement, une nouvelle entrée apparaît dans l'historique.

## 6. Indicateur non-éditable et chat (US5)

1. Cliquer sur un indicateur dont le code n'est **pas** dans `SCORING_EDITABLE_INDICATEUR_CODES`.
2. Le drawer s'ouvre normalement, mais le bouton « Modifier » affiche le tooltip « Édition disponible via le chat » et au clic, un toast informe l'utilisateur et le chat s'ouvre avec un message contextualisé.

## 7. Recalcul manuel (US6)

1. Sur `/scoring/BOAD`, cliquer « Recalculer ».
2. Spinner < 100 ms ; nouveau score affiché ; nouvelle date ; nouvelle entrée dans `HistoryChart`.
3. Double-cliquer sur « Recalculer » → le second clic est ignoré (anti double-clic).

## 8. Historique (US7)

Pour générer plusieurs points : refaire 2-3 fois `recompute` (étape 3, option B). L'`HistoryChart` doit afficher autant de points, hover = `Date FR + score + version v.X`.

## 9. Snapshot (US8)

1. Activer le toggle « Voir snapshot ».
2. Sélectionner une date historique dans le sélecteur.
3. Le bandeau « SNAPSHOT du JJ/MM/AAAA — version v.X » apparaît en haut.
4. Vérifier que les boutons « Modifier » et « Recalculer » sont **désactivés** (pas masqués).
5. Désactiver le toggle → retour à l'état courant, boutons réactivés.

## 10. Source révoquée (edge case)

Pour tester :

```bash
# (admin uniquement) marquer une source comme révoquée via /admin/sources/{id}
TOKEN_ADMIN="<jwt admin>"
SRC_ID="<source_id>"
curl -s -X PATCH \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"status":"revoked"}' \
  http://localhost:8010/admin/sources/$SRC_ID
```

Recharger `/scoring/BOAD` côté PME → l'indicateur dont la source est révoquée affiche un badge avertissement et la valeur grisée.

## 11. Sync chat ↔ scoring (US11)

Avec deux onglets ouverts : (a) `/scoring/BOAD`, (b) le chat F41. Modifier un indicateur depuis le chat (via une requête tool ou manuellement) → l'onglet (a) doit voir son score se rafraîchir sans action manuelle (bus `entity_updated`).

## 12. Empty states

- Pour `EmptyNoCalculation` : effacer l'`account_id` ciblé via une requête admin `DELETE /admin/score-calculations?account_id=...` (ou créer un nouveau compte sans calcul) → la page affiche le CTA « Lancez votre premier diagnostic ».
- Pour `MissingIndicatorsList` masquée : compléter tous les champs du profil → couverture 100 % → la section disparaît.

## 13. Accessibilité et reduced-motion

- Activer `prefers-reduced-motion: reduce` dans les DevTools → vérifier que le radar n'a pas d'animation et que le drawer n'a pas de slide.
- Naviguer toute la page au clavier (Tab) → focus visible, ordre logique : tabs référentiel → recalc → comparer → accordéons → rows → bottom sheet (focus trap).
- Vérifier le tableau `sr-only` sous le radar via les outils DevTools.

## 14. Tests automatisés

```bash
# Backend
cd backend && source .venv/bin/activate
pytest tests/scoring/test_history_endpoint.py -v

# Frontend unit + components
cd frontend && pnpm vitest run

# Frontend e2e
cd frontend && pnpm test:e2e --grep scoring
```

## 15. Troubleshooting

| Symptôme | Cause probable | Action |
|---|---|---|
| `/scoring/BOAD` → 404 dans le toast | Référentiel non publié | Publier via `/admin/referentiels/BOAD/publish` |
| Score `null` après `recompute` | Aucun indicateur mappé renseigné | Compléter le profil entreprise (étape 2) |
| Bouton « Modifier » toujours grisé | Indicateur hors `SCORING_EDITABLE_INDICATEUR_CODES` | Édition via chat |
| Historique vide | Un seul calcul existant | Refaire `recompute` 2-3 fois |
| Drawer ne se ferme pas | Focus trap bloqué | `Escape` ou clic en dehors |
