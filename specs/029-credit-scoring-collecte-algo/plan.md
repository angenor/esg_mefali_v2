# Implementation Plan F29 — Credit Scoring Collecte & Algo (MVP)

**Branch**: `029-credit-scoring-collecte-algo` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)

## Summary

Backend-only MVP : (1) table `credit_data` (déclaratif + statement Mobile Money normalisé) avec gating consentements F05, (2) table `credit_score` append-only, (3) service `CreditScoringService` (règles pondérées sourcées, 3 scores), (4) endpoints `POST /me/credit-data`, `POST /me/credit-data/mobile-money`, `GET /me/credit-score`, `POST /me/credit-score/recompute`, `GET /methodologie/credit-scoring`, (5) seed du référentiel `credit_scoring_methodology` versionné F09 + F04. **DEFERRED** : page Vue, intégrations live Mobile Money, mappers Wave/Orange/MTN/Free, analyse photos LLM, scraping social, skill_credit_score full LLM orchestration.

## Technical Context

- **Language**: Python 3.11 (FastAPI). Pas de frontend en MVP.
- **Storage**: PostgreSQL 16 (existant), advisory lock par entreprise pour la sérialisation des recalculs.
- **Tests**: pytest + pytest-asyncio + httpx.
- **Dépendances** :
  - F03 (sources `published`/`verified` requises pour les `source_id` des facteurs méthodologie),
  - F04 (audit `record_audit`, versioning méthodologie),
  - F05 (`RequiresConsent(MOBILE_MONEY|EXPLOITATION_PHOTOS)`),
  - F09 (`Referentiel` kind=`credit_scoring_methodology` + `Critere` pour les facteurs),
  - F11 (`Entreprise`),
  - F12 (`Projet` lecture pour impact_vert),
  - F23 (lecture `score_calculation` ESG le plus récent par entreprise),
  - F28 (lecture `carbon_footprint` le plus récent par entreprise).

## Constitution Check

| # | Principe | Status |
|---|----------|--------|
| P1 | Sourçage anti-hallucination | OK : tous les facteurs méthodologie référencent un `source_id` F09 (seed) ; refus de seed si source non publiée. |
| P2 | RLS multi-tenant | OK : `credit_data` et `credit_score` portent `account_id`, RLS active ; admin lit tout. |
| P3 | Audit append-only | OK : `record_audit('credit_data','create',…)`, `record_audit('credit_score','compute',…)`. |
| P4 | Versioning méthodologie | OK : `methodologie_version` snapshoté dans `credit_score` ; nouvelle pondération → nouvelle version Référentiel. |
| P5 | Money typé | N/A (scores sans devise). Mobile Money montants stockés en `int` XOF dans payload. |
| P6 | Pivot indicateur | N/A. |
| P7 | Plateforme fermée | OK : `/me/*` PME, `/methodologie/credit-scoring` lecture publique sans auth (whitelisted). |
| P8-10 | N/A | OK |

## Phase 0 — Research

- Lookup ESG le plus récent : `SELECT * FROM score_calculation WHERE entreprise_id=:e ORDER BY computed_at DESC LIMIT 1` (lecture défensive).
- Lookup empreinte la plus récente : `SELECT * FROM carbon_footprint WHERE entreprise_id=:e ORDER BY computed_at DESC LIMIT 1`.
- Lookup méthodologie active : `SELECT * FROM referentiel WHERE kind='credit_scoring_methodology' AND status='published' ORDER BY version DESC LIMIT 1`.
- Advisory lock : `SELECT pg_advisory_xact_lock(hashtext('credit_score:' || :entreprise_id))`.

## Phase 1 — Design

```
backend/app/credit/
  __init__.py
  engine.py             # règles pures: compute_solvabilite, compute_impact, compute_combined, compute_factors
  csv_parser.py         # parser CSV générique normalisé + indicateurs dérivés
  service.py            # CreditScoringService (orchestre db + lock + audit)
  schemas.py            # Pydantic
  router.py             # 5 endpoints
  methodology_seed.py   # seed Référentiel v1 (idempotent)

backend/app/models/credit_data.py
backend/app/models/credit_score.py
backend/alembic/versions/0019_f29_credit.py

backend/tests/unit/credit/test_csv_parser.py
backend/tests/unit/credit/test_engine.py
backend/tests/integration/credit/test_router.py
```

### Data Model

`credit_data`
- `id UUID PK`, `account_id UUID NOT NULL`, `entreprise_id UUID NOT NULL`,
- `kind ENUM('mobile_money','declaratif','photos','publique')`,
- `payload_json JSONB NOT NULL`,
- `consent_id UUID NULL`,
- `uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()`,
- `valid_until TIMESTAMPTZ NULL`.
- RLS : `USING (account_id = current_setting('app.account_id')::uuid OR current_setting('app.role')='admin')`.

`credit_score` (append-only)
- `id UUID PK`, `account_id UUID NOT NULL`, `entreprise_id UUID NOT NULL`,
- `solvabilite SMALLINT NOT NULL CHECK 0..100`,
- `impact_vert SMALLINT NOT NULL CHECK 0..100`,
- `combine SMALLINT NOT NULL CHECK 0..100`,
- `facteurs JSONB NOT NULL` (liste {name, definition, value, weight, contribution, source_id}),
- `methodologie_version INT NOT NULL`,
- `coherence_warning BOOLEAN NOT NULL DEFAULT FALSE`,
- `computed_at TIMESTAMPTZ NOT NULL DEFAULT now()`.
- Index `(entreprise_id, computed_at DESC)`.
- RLS identique à `credit_data`.

### Algorithme MVP (règles pondérées sourcées)

Solvabilité (poids cumulé 1.00) :
- `mm_volume` (0.25) — moyenne mensuelle XOF / 1 000 000 capée à 1.0.
- `mm_regularite` (0.20) — `1 - (ecart_type / moyenne)` capée à [0, 1].
- `entreprise_anciennete` (0.15) — années depuis création / 10 capée à 1.0.
- `entreprise_taille` (0.10) — `log(employes+1) / log(101)` capée à 1.0.
- `paiements_reguliers` (0.15) — 1.0 si déclaré true, 0.5 sinon.
- `diversification_clients` (0.15) — `min(nb_clients/10, 1.0)`.

Impact vert (poids cumulé 1.00) :
- `esg_global` (0.40) — `score_global / 100` du `ScoreCalculation` le plus récent.
- `carbone_intensite` (0.30) — `1 - min(total_tco2e / 1000, 1.0)` (plus c'est bas, mieux).
- `projets_verts` (0.20) — `min(nb_projets_verts / 3, 1.0)`.
- `alignement_odd` (0.10) — `min(nb_odd_alignes / 5, 1.0)`.

Combiné : `combine = round(α * solvabilite + β * impact_vert)` (α=0.6, β=0.4 par défaut, persistés dans le seed).

Facteurs absents → `value=null, contribution=0` ; `coherence_warning=true` si la couverture (somme des poids des facteurs disponibles) de solvabilité ou impact_vert < 50 %, ou si `combine > 80` sans Mobile Money ni ESG.

## Phase 2 — Tasks

Voir [tasks.md](./tasks.md).

## Complexity Tracking

Aucune violation. Lectures défensives (None-safe) sur ESG et empreinte carbone si modèles absents.
