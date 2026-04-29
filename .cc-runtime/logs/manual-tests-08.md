# Manual Tests — F08 Catalogue Fonds, Intermédiaires & Offres

**Branche** : `008-catalog-fonds-intermediaires-offres`
**Date** : 2026-04-29
**Scope MVP testé** : Phases 1 + 2 + 3 (US1 Fonds) + 4 (US2 Intermédiaire) + 5 (US3 Accreditation) + 6 (US4 Offre + /effective).

## Pré-requis

```bash
docker compose up -d postgres
cd backend && source .venv/bin/activate
alembic upgrade head
pytest tests/integration/admin/test_admin_fonds.py \
       tests/integration/admin/test_admin_intermediaires.py \
       tests/integration/admin/test_admin_accreditations.py \
       tests/integration/admin/test_admin_offres.py \
       tests/unit/test_effective_calculator.py -q
# → 36 passed
```

## Sanity smoke (curl)

Tous les exemples supposent un admin authentifié (cookies `mefali_at` + header
`X-CSRF-Token`). Un test E2E manuel se déroule comme suit :

### 1. Création Fonds (US1)

```bash
curl -X POST http://localhost:8000/admin/fonds/ \
  -H "Content-Type: application/json" \
  -b cookies.txt -H "X-CSRF-Token: $CSRF" \
  -d '{
    "name": "Green Climate Fund",
    "organisation": "GCF",
    "type": "multilateral",
    "thematique": ["climat", "adaptation"],
    "instruments": ["don", "pret_concessionnel"],
    "eligibilite_geo": ["CI", "SN", "TG"],
    "submission_mode": "rolling",
    "criteres_json": [
      {"key":"max_amount","operator":"max","value":10000000,
       "unit":"USD","source_id":"<verified-source-uuid>"}
    ],
    "documents_requis_json": [],
    "frais_json": {"origination_pct":1.0,"currency":"EUR"},
    "delais_json": {"instruction_jours":30},
    "source_ids": ["<verified-source-uuid>"]
  }'
# → 201, ETag: "v1"
```

### 2. Publish gate (US1, FR-013)

```bash
curl -X POST http://localhost:8000/admin/fonds/<id>/publish \
  -b cookies.txt -H "If-Match: \"v1\"" -H "X-CSRF-Token: $CSRF"
# Avec source verified : 200, status=published
# Avec source pending  : 422 sources_not_verified
```

### 3. Création Intermédiaire (US2)

```bash
curl -X POST http://localhost:8000/admin/intermediaires/ \
  -H "Content-Type: application/json" -b cookies.txt -H "X-CSRF-Token: $CSRF" \
  -d '{
    "name": "BOAD",
    "type": "banque_locale",
    "pays": ["CI", "SN", "BF"],
    "zone_op": "UEMOA",
    "frais_json": {"marge_pct":0.5,"currency":"EUR"},
    "delais_json": {"decaissement_jours":60},
    "criteres_json": [
      {"key":"max_amount","operator":"max","value":5000000,
       "unit":"USD","source_id":"<verified-source-uuid>"}
    ],
    "documents_requis_json": [],
    "source_ids": ["<verified-source-uuid>"]
  }'
# → 201
```

### 4. Création Accreditation (US3)

```bash
curl -X POST http://localhost:8000/admin/accreditations/ \
  -H "Content-Type: application/json" -b cookies.txt -H "X-CSRF-Token: $CSRF" \
  -d '{
    "intermediaire_id": "<inter-id>",
    "fonds_id": "<fonds-id>",
    "valid_from": "2026-01-01",
    "valid_to": "2027-12-31",
    "plafond_money": {"amount": 10000000, "currency": "USD"},
    "source_id": "<verified-source-uuid>",
    "notes": "Accréditation officielle GCF"
  }'
# → 201

# Helper /is_active :
curl http://localhost:8000/admin/accreditations/<id>/is_active -b cookies.txt
# → {"id":"...", "active": true, "valid_from":"2026-01-01", "valid_to":"2027-12-31"}
```

### 5. Création Offre (US4)

```bash
curl -X POST http://localhost:8000/admin/offres/ \
  -H "Content-Type: application/json" -b cookies.txt -H "X-CSRF-Token: $CSRF" \
  -d '{
    "fonds_id": "<fonds-id>",
    "intermediaire_id": "<inter-id>",
    "name": "GCF via BOAD",
    "accepted_languages": ["fr","en"],
    "criteres_offre_specifiques": [],
    "documents_specifiques": [],
    "frais_specifiques": {},
    "delais_specifiques": {},
    "source_ids": ["<verified-source-uuid>"]
  }'
# Sans accreditation active → 409 no_active_accreditation
# Avec accreditation active → 201
```

### 6. Calcul /effective (US4 cœur métier)

```bash
curl http://localhost:8000/admin/offres/<id>/effective -b cookies.txt | jq .
# → EffectiveResponse :
#   - fonds_layer : critères / documents / frais / délais issus du Fonds
#   - intermediaire_layer : idem côté Intermédiaire
#   - offre_layer : overrides spécifiques
#   - criteres_effectifs : fusion (max→min, in→intersect)
#   - documents_effectifs : union par document_id
#   - frais_effectifs : somme par devise (warning mixed_currency_fees si N>1)
#   - delais_effectifs_jours : somme entière
#   - effective_warning : list[str]
#   - snapshot_hash : sha256
```

**Cas attendus (les 5 cas d'école — couverts par `test_effective_calculator.py`)** :

| # | Fonds | Intermédiaire | Résultat attendu |
|---|-------|--------------|------------------|
| 1 | GCF max 10M USD | BOAD max 5M USD | criteres_effectifs.max_amount = 5M |
| 2 | GCF pays in CI/SN/TG | UNDP pays in CI/SN/BF | pays = [CI, SN] |
| 3 | FEM instruments=don,pret | PNUD instruments=don,garantie | instruments = [don] |
| 4 | SUNREF max 10M EUR | Ecobank max 5M EUR | max_amount = 5M EUR |
| 5 | FNE-CI pays=[CI] | banque RDC pays=[RDC] | pays=[], warning incompatible_countries |

## Tests automatisés

| Suite | Fichier | Tests |
|-------|---------|-------|
| Calculateur effective (TDD) | `tests/unit/test_effective_calculator.py` | 18 |
| Fonds CRUD + publish + ETag | `tests/integration/admin/test_admin_fonds.py` | 6 |
| Intermédiaire CRUD + publish | `tests/integration/admin/test_admin_intermediaires.py` | 2 |
| Accreditation + is_active | `tests/integration/admin/test_admin_accreditations.py` | 6 |
| Offre + /effective + uniqueness | `tests/integration/admin/test_admin_offres.py` | 4 |
| **Total** | | **36** |

Coverage F08 : **83%** sur `app/api/admin/*`, `app/core/effective_calculator.py`,
`app/schemas/{critere,fonds_source,intermediaire,accreditation,offre,effective}.py`.
Coverage globale : **85.16%**.

## Invariants Module 0 vérifiés

- ✓ Sourcing : Fonds, Intermédiaire, Offre exigent ≥ 1 source verified pour publish
  (réutilise `verify_sources_or_422` F06). Accreditation a `source_id` NOT NULL.
- ✓ Audit (F04) : `write_admin_event` est appelé sur create/update/publish avec
  `source_of_change='admin'` et diff before/after.
- ✓ Money typé : `Money {amount, currency}` (whitelist XOF/EUR/USD/GHS/NGN/MAD/GBP)
  via Pydantic.
- ✓ RLS : politique alternative pour catalogue global :
  `SELECT` = published OR app.is_admin ; `INSERT/UPDATE/DELETE` = app.is_admin only.
  Accreditation a un read public (relation pivot).
- ✓ ETag/If-Match (F06) : tous les PUT/PUBLISH exigent l'en-tête. 412 si mismatch.
- ✓ TDD : 5 cas d'école `effective_calculator` écrits avant l'implémentation.

## Différé (post-MVP)

Voir `tasks.md` annotations `[DEFERRED]` :
- Phase 7 (hooks needs_refresh + outdated lazy check) — fonctionnel en lecture pure
  via `compute_effective` ; agent de mutation reportable.
- Phase 8 (US5 comparator UI) — endpoints `GET /admin/fonds/{id}/intermediaires`
  et `GET /admin/intermediaires/{id}/fonds` sont déjà livrés (FR-006/FR-007).
- Phase 9 (US6 submission_mode) — backend déjà implémenté (deadline override Offre
  prime sur Fonds) ; UI toggle deferred.
- Phase 10 (catalog public PME `/catalog/*`) — non livré ; nécessite F11 PME profile.
- Phase 11 (polish, perf, accessibilité, frontend) — déféré.
- **Frontend complet (toutes pages Vue/Pinia)** — déféré ; le backend est consommable
  via OpenAPI auto-générée.
