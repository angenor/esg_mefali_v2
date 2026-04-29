# F23 — Manual tests log (Scoring ESG MVP)

**Branch** : `023-scoring-esg-multi-referentiels`
**Date** : 2026-04-29
**Scope MVP livré** : US1 (score Mefali), US2 (multi-référentiels), US3 spec (détail couverts/manquants), US4 (recalcul à la demande), US5 spec (grille E/S/G dérivée).
**DEFERRED** : US3 brouillon (activation contextuelle fonds+intermédiaire), US5 brouillon (benchmarking), US6 (history), recalcul auto debounced, frontend Vue.

## Pré-requis

```bash
cd backend
alembic upgrade head           # applique la migration 0016
docker compose up -d postgres
```

## Tests automatisés (verts)

```bash
cd backend
.venv/bin/python -m pytest tests/scoring/ --cov=app.scoring -q
```

Résultat constaté à l'implémentation :
- 67 tests passés (5 fichiers : engine, normalizer, value_source, service_helpers, schemas, router).
- Couverture mesurée : 80.95 % (cible ≥ 80 % atteinte).
- Lint : `ruff check app/scoring/ tests/scoring/` → All checks passed.

## Tests manuels HTTP (à exécuter avec DB peuplée)

### 1. Setup minimal (à exécuter une fois en SQL ou via seed admin F09)

```sql
-- Source démo
INSERT INTO source (id, official_url, doc_title, status, account_id)
VALUES ('11111111-0000-0000-0000-000000000001', 'https://example.test/F23',
        'Source F23 démo', 'verified', '<account_admin_id>');

-- Référentiel publié
INSERT INTO referentiel (id, code, name, type, formula_type, version, valid_from,
                          status, etag, logical_id, created_at, updated_at)
VALUES ('22222222-0000-0000-0000-000000000001', 'TEST_REF', 'Demo F23',
        'transverse', 'weighted_sum', 1, now(), 'published', 'demo',
        '22222222-0000-0000-0000-000000000001', now(), now());

-- Indicateurs publiés
INSERT INTO indicateur (id, code, name, pillar, value_type, version, status,
                         etag, valid_from, logical_id, created_at, updated_at)
VALUES
  ('33333333-0000-0000-0000-000000000001','DEMO_E1','Demo E','E','numeric',1,
   'published','e','2026-04-29','33333333-0000-0000-0000-000000000001',now(),now()),
  ('33333333-0000-0000-0000-000000000002','DEMO_S1','Demo S','S','boolean',1,
   'published','s','2026-04-29','33333333-0000-0000-0000-000000000002',now(),now());

-- Liens référentiel ↔ indicateurs (poids + source)
INSERT INTO referentiel_indicateur (referentiel_id, indicateur_id, poids,
                                      seuil_min, seuil_max, source_id) VALUES
  ('22222222-0000-0000-0000-000000000001',
   '33333333-0000-0000-0000-000000000001', 1.0, 0, 1000000,
   '11111111-0000-0000-0000-000000000001'),
  ('22222222-0000-0000-0000-000000000001',
   '33333333-0000-0000-0000-000000000002', 1.0, NULL, NULL,
   '11111111-0000-0000-0000-000000000001');
```

### 2. Login PME

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"pme@test.local","password":"<pwd>"}' | jq -r .access_token)
ENT_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/me/entreprise | jq -r .id)
```

### 3. POST recompute → 201

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/me/scoring/entreprise/${ENT_ID}/recompute?referentiel=TEST_REF"
```

Attendu : 201 + JSON `ScoreDetailOut` avec `referentiel_code`, `score_global`, `scores_by_pillar`, `indicateurs_couverts/manquants`, `sources_used`.

### 4. GET liste → 200

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/me/scoring/entreprise/${ENT_ID}
```

Attendu : 200 + `{entity_type, entity_id, scores: [ScoreSummaryOut...]}`.

### 5. GET détail → 200

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/me/scoring/entreprise/${ENT_ID}/TEST_REF
```

Attendu : 200 + `ScoreDetailOut`.

### 6. Sécurité

- Sans token → 401 (vérifié par `tests/scoring/test_router.py::TestAuthGate`).
- Référentiel inexistant → 404 (handled by `compute_and_persist` → `ReferentielNotFound`).
- Cross-tenant : RLS Postgres + check `EntityNotAccessible` côté service → 404.

## Notes pour les tests d'intégration DB

Les tests présents (`tests/scoring/`) sont des unitaires purs (pas de DB requise).
Les tests d'intégration HTTP avec RLS contextuel (vrai SQL avec `SET LOCAL`)
sont **différés** post-MVP : ils nécessitent la fixture commune full-stack
(account, account_user, JWT, entreprise) qui demande une refacto plus large
des fixtures partagées hors scope F23.

## Logs annexes

- Spec et plan : `specs/023-scoring-esg-multi-referentiels/`.
- Clarify trace : `.cc-runtime/logs/clarify-23.log`.
- Pas de fixloop nécessaire (tests verts en première itération).
