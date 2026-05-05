# Quickstart — F51

**Branch**: `051-matching-candidatures-simulateur-ui` | **Date**: 2026-05-05

Comment lancer F51 en dev local après `make setup` initial.

## 1. Prérequis

- Postgres up (`make db-up`).
- Backend `.venv` créé (`cd backend && source .venv/bin/activate`).
- Frontend deps installées (`cd frontend && pnpm install`).
- Seeds catalogue offres existants (F08) : au moins 10 offres publiées avec `intermediaire.geolocation` renseignée pour 3+ d'entre elles, et `documents_requis` non vide.
- Au moins un projet ESG renseigné (F11/F12).

## 2. Migration DB

```bash
cd backend && source .venv/bin/activate
alembic upgrade head    # applique 0051_candidatures_wizard_simulateur_savee
```

Vérifications :

```bash
psql -h localhost -U mefali -d mefali_dev -c "\d+ candidature" | grep -E "step_courant|progression_pct|draft_snapshot|submitted_at|submitted_snapshot"
psql -h localhost -U mefali -d mefali_dev -c "\dt simulation_savee"
psql -h localhost -U mefali -d mefali_dev -c "\d+ simulation_savee" | grep policy
```

## 3. Démarrage des serveurs

Cf. CLAUDE.md (3 terminaux) :

```bash
make db-up            # T1
make backend          # T2 — port 8010
make frontend         # T3 — port 3001
```

## 4. Parcours de validation manuelle

### A. Matching

1. Login PME, vérifier qu'au moins un projet existe (sinon en créer un).
2. Aller sur `http://localhost:3001/matching`.
3. La liste affiche les offres triées par score décroissant (US1).
4. Appliquer filtres `type=subvention` + `montant_max=100000` → URL `/matching?type=subvention&montant_max=100000`. Recharger : filtres persistent (US2, FR-002).
5. Cliquer onglet "Carte" → Leaflet se charge en lazy chunk, pins visibles pour les intermédiaires géolocalisés (US3).
6. Cocher "Ajouter au comparateur" sur 2 offres → bouton "Comparer (2)" actif.
7. Tenter une 4ᵉ → toast "Maximum 3".
8. Cliquer "Comparer" → `/matching/compare` affiche table side-by-side (US4, SC-005).
9. Ouvrir drawer détail offre → cliquer "Préparer ma candidature" → redirection `/candidatures/new?offre_id=...&projet_id=...`.

### B. Wizard candidature

1. Étape 1 (offre+projet) — pré-remplie depuis l'URL, valider.
2. Étape 2 (snapshot data PME) — read-only ; cliquer "Modifier dans profil" → ouvre `/profil` dans nouvel onglet (P8).
3. Étape 3 (documents) — bandeau "documents manquants" visible (FR-009). Lien vers upload F50. Uploader un PDF, le lier via `checklist_key`. Bandeau disparaît dès complétion.
4. Étape 4 (réponses libres) — chat F41 contextuel ouvert. Tester une question → toute saisie interactive (radio, slider) s'affiche dans bottom sheet F39, jamais inline (P10). Bouton "Répondre librement" présent.
5. Test reprise : à mi-étape, fermer l'onglet ; recharger `/candidatures` → ligne "brouillon" visible avec progression. Cliquer "Reprendre" → wizard rouvre à l'étape interrompue avec saisies préservées (SC-007).
6. Étape 5 (récap) — relire, cocher "Je comprends que ma candidature sera figée", cliquer "Soumettre".
7. Modale double-confirm apparaît → bouton désactivé tant que checkbox non cochée → confirmer.
8. Vérifier en DB :

   ```sql
   SELECT statut, submitted_at, submitted_snapshot_json IS NOT NULL FROM candidature WHERE id = '...';
   -- → soumise | <ts> | t
   SELECT submitted_snapshot_json -> 'schema_version' FROM candidature WHERE id = '...';
   -- → "1"
   ```

9. Tenter `PATCH /me/candidatures/{id}/draft` post-submit → 422 `already_submitted`.
10. Tenter UPDATE direct en DB sur `submitted_snapshot_json` → trigger `P4 violation` (test contre `psql` en superuser pour reproduire).

### C. Simulateur

1. Aller sur `/simulateur`.
2. Bouger le slider "Montant" rapidement de 50k → 200k → 350k → vérifier qu'**une seule** requête finale part (debounce 300 ms, AbortController).
3. Charts F40 mettent à jour en < 200 ms perçus (SC-003), pas de flash blanc.
4. Cliquer "Sauvegarder cette simulation" → bottom sheet F39 demande label. Confirmer.
5. Aller `/simulateur/historique` → ligne visible.
6. Retour `/simulateur`, cliquer "Trouver des offres compatibles" → redirection `/matching?montant_max=...&duree_max=...` avec filtres pré-appliqués (SC-006, US15 spec).

## 5. Tests automatisés

```bash
# Backend — unit + integration
cd backend && source .venv/bin/activate
pytest tests/unit/candidatures tests/unit/simulation tests/unit/matching -v
pytest tests/integration/test_candidatures_wizard_api.py tests/integration/test_simulateur_history_api.py tests/integration/test_offres_listing_api.py -v
pytest --cov=app/candidatures --cov=app/simulation --cov=app/matching --cov-report=term-missing  # ≥ 80 %

# Frontend — unit
cd frontend && pnpm vitest run tests/unit/matching tests/unit/candidatures tests/unit/simulateur

# E2E Playwright
pnpm playwright test tests/e2e/matching-flow.spec.ts tests/e2e/candidatures-wizard.spec.ts tests/e2e/simulateur-flow.spec.ts
```

## 6. Pièges connus

- **Postgres trigger P4** : si vous tentez de modifier `submitted_snapshot_json` via `psql` en superuser pour debug, vous obtiendrez une exception `P4 violation`. C'est attendu. Pour reset un dossier de test, supprimer la candidature et la recréer.
- **Comparateur cross-projet** : changer de projet actif vide le comparateur (research §4) — comportement voulu, pas un bug.
- **Carte Leaflet 1er rendu** : peut prendre ~500 ms (chunk async + tile fetch). Ne pas bloquer LCP de la liste cards.
- **Money formatting** : si `amount` arrive en `number` au lieu de `string`, c'est une régression P5 — corriger côté API ou parsing.

## 7. Rollback

```bash
alembic downgrade -1     # rollback 0051
```

Le downgrade :
- DROP TRIGGER + FUNCTION `candidature_no_mutation_after_submit`.
- DROP TABLE `simulation_savee`.
- ALTER TABLE candidature DROP COLUMN x5.

⚠ Tout brouillon stocké dans `draft_snapshot_json` ou snapshot soumis dans `submitted_snapshot_json` sera **perdu**. Sauvegarder via `pg_dump` avant downgrade en environnement non-dev.
