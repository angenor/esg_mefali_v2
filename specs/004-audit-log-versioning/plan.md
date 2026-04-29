# Implementation Plan: Audit Log Append-Only & Versioning

**Branch**: `004-audit-log-versioning` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-audit-log-versioning/spec.md`

## Summary

F04 delivers two transversal Module 0 invariants on top of the F01/F02/F03 baseline:

1. An **append-only `audit_log`** table protected by Postgres privilege revocations (no UPDATE / DELETE / TRUNCATE for the application role) and by RLS scoped on `account_id`, fed by a single backend helper `record_audit(...)` invoked explicitly by every business mutation (no triggers in MVP). A Python decorator wraps LLM mutation tool handlers so they journal automatically with `source_of_change='llm'` (consumed later by F17). Read-side `GET /audit-log` (paginated, filterable, RLS-enforced) plus CSV/JSON export complete the surface.
2. **Temporal versioning** of the seven catalogue tables (`referentiel`, `indicateur`, `critere`, `formule`, `seuil`, `facteur_emission`, `template`) via the columns `version`, `valid_from`, `valid_to`, `parent_id`, `logical_id`, an `EXCLUDE` constraint preventing temporal overlap per `logical_id`, the helpers `publish_new_version(...)` (transactional, optimistic-lock via `If-Match`) and `get_active(entity_type, logical_id, at_timestamp?)`, plus the immutable `candidature.snapshot_json` (JSON Schema v1) populated atomically at submission and recomputable via `POST /candidatures/{id}/recompute-from-snapshot`. The Vue 4 `<VersionBadge>` component renders the badge in French.

Approach: SQL migration + Python helpers + thin FastAPI routers + one Nuxt component. No new external dependency. All design choices align with the constitution's NON NÉGOCIABLE principles P3 and P4.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript 5+ / Vue 3 inside Nuxt 4 (frontend), SQL (PostgreSQL 16).
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2 (`extra='forbid'`), `psycopg[binary]`, Nuxt 4, Pinia, TailwindCSS v4. No new third-party library required.
**Storage**: PostgreSQL 16 + pgvector (single Docker service). Audit log: BIGSERIAL PK, JSONB columns, single global table with RLS. Versioned tables: existing F01 tables altered in place, plus `EXCLUDE USING gist` constraint on `(logical_id WITH =, tstzrange(valid_from, COALESCE(valid_to, 'infinity')) WITH &&)` (requires `btree_gist`).
**Testing**: pytest (backend, async), pytest-postgresql/Testcontainers Postgres, Vitest + @vue/test-utils (frontend component test), Playwright for the snapshot recompute E2E flow.
**Target Platform**: Linux server (FastAPI + Postgres in Docker for Postgres only); Nuxt 4 SSR. Browsers: evergreen Chromium / Firefox / Safari.
**Project Type**: Web application (backend FastAPI + frontend Nuxt 4 already in place from F01).
**Performance Goals**: ≥100 audit_log inserts/sec on the dev container with concurrent 10 reads/sec under 200 ms p95; first audit-log page (≤20 rows) under 500 ms p95 on a 1 M-row tenant.
**Constraints**: Append-only (no UPDATE/DELETE on `audit_log` for `app_user`); strict RLS by `account_id` from `app.current_account_id` (F02 convention); snapshot immutable post-submission; no LLM hard-coded model; FCFA-EUR peg at 655.957 (no Money math required by this feature, but Decimal-typed scores in snapshot).
**Scale/Scope**: MVP target — up to 1 M audit rows per tenant, ~10 k versioned-entity rows total, ~100 candidatures per tenant in year 1. Partitioning explicitly post-MVP.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Toute donnée factuelle introduite par cette feature pointe-t-elle vers une `Source` `verified` ? Les nouveaux champs catalogue ont-ils `source_id NOT NULL` ? | ✅ N/A — no new factual claim is introduced; the snapshot stores `sources` references but does not bypass F03 verification. The decorator preserves F03's `source_id NOT NULL` constraints. |
| P2 | Multi-tenant RLS | Toute nouvelle table métier porte-t-elle `account_id` + politique RLS ? Les accès cross-tenant retournent-ils 404 ? | ✅ `audit_log` carries `account_id` and `ENABLE ROW LEVEL SECURITY` with the `app.current_account_id` policy. Cross-tenant queries return empty result sets and the API surfaces 404 for direct-id lookups. |
| P3 | Audit log append-only | Toute mutation introduite est-elle journalisée avec `source_of_change` ∈ {manual, llm, import, admin} ? | ✅ This feature *delivers* P3. `system` is added (constitution lists 4 enum values; F04 spec adds `system` for migrations; this is an EXPANSION, not a contradiction, and aligns with F04 markdown text). Documented in research.md. |
| P4 | Versioning + snapshot candidatures | Les nouveaux référentiels/critères/formules portent-ils `version`, `valid_from`, `valid_to` ? Les candidatures stockent-elles un `snapshot_json` immuable ? | ✅ This feature *delivers* P4. Seven tables altered, `EXCLUDE` constraint enforces no overlap, candidature snapshot is immutable at API and DB-policy layers. |
| P5 | Money typé | Toute valeur monétaire utilise-t-elle `Money = {amount: Decimal, currency}` ? | ✅ Snapshot stores monetary scores as `Money` objects (Decimal serialised to string in JSONB) — no new Money math introduced; recompute reuses the F23 scoring layer's Decimal arithmetic. |
| P6 | Pivot Indicateur unique | Les données ESG sont-elles stockées comme valeurs d'`Indicateur` ? | ✅ N/A — no new ESG capture path introduced. The snapshot references existing `Indicateur` rows by `logical_id + version`, never duplicates by axis E/S/G. |
| P7 | Plateforme fermée aux intermédiaires | La feature évite-t-elle tout rôle utilisateur Intermédiaire/Bank/Fund ? | ✅ Only PME and Admin roles touch this feature; export endpoints respect the same RBAC; no webhook to external party. |
| P8 | Édition manuelle + sync LLM | Tout champ alimenté par le LLM est-il modifiable manuellement ? La mutation manuelle invalide-t-elle le contexte LLM en temps réel ? | ✅ The audit log is read-only for users by design (constitutional invariant overrides P8 for this specific append-only entity). Versioned entities remain editable through `publish_new_version` from both manual UI (Phase 2/F09) and LLM tools (F17). Snapshot is immutable post-submission, which is the explicit P4 requirement and supersedes P8's editability default for this single field. |
| P9 | Tool-use LLM fiable | Nouveaux tools LLM ? | ✅ N/A — no LLM tool delivered by F04 itself. The decorator is *infrastructure* used by F17. The decorator validates Pydantic v2 inputs (`extra='forbid'`) before delegating. |
| P10 | UX bottom sheet | Composants interactifs en bottom sheet ? | ✅ `<VersionBadge>` is a *display* component (no input); the audit-log read view (P2 user story 3) is delivered visually only by F32 — F04 only provides the read endpoint. No interactive form is shipped here. |

**Result**: All 10 gates pass. No `Complexity Tracking` entry required.

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ; LLM via OpenRouter ; embeddings Voyage `voyage-3.5` (1024 dim).
- Dev local : backend en `.venv`, Postgres seul service dockerisé, frontend en `pnpm dev`.
- Hébergement production : Europe ou Afrique de l'Ouest uniquement.
- Langue : français par défaut (badge en français only).

## Project Structure

### Documentation (this feature)

```text
specs/004-audit-log-versioning/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── audit-log.openapi.yaml
│   ├── candidature-recompute.openapi.yaml
│   └── snapshot.schema.json
├── checklists/
│   └── requirements.md  # Spec quality checklist (already present)
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── alembic/
│   └── versions/
│       └── 0004_audit_log_and_versioning.py   # adds audit_log, alters 7 tables, adds candidature snapshot
├── app/
│   ├── audit/
│   │   ├── __init__.py
│   │   ├── helper.py                           # record_audit(...)
│   │   ├── decorator.py                        # @journal_llm_mutation
│   │   ├── blacklist.py                        # field redaction
│   │   ├── schemas.py                          # Pydantic models
│   │   └── service.py                          # query / export
│   ├── versioning/
│   │   ├── __init__.py
│   │   ├── helpers.py                          # publish_new_version, get_active
│   │   └── exceptions.py                       # OptimisticLockError
│   ├── snapshot/
│   │   ├── __init__.py
│   │   ├── builder.py                          # build_candidature_snapshot
│   │   ├── schema.py                           # JSON Schema v1
│   │   └── recompute.py                        # recompute_from_snapshot
│   ├── api/
│   │   ├── audit_log.py                        # GET /audit-log, exports
│   │   └── candidatures_recompute.py           # POST /candidatures/{id}/recompute-from-snapshot
│   └── models/
│       ├── audit_log.py                        # SQLAlchemy model
│       └── versioned_mixin.py                  # mixin for versioned tables
└── tests/
    ├── unit/
    │   ├── audit/test_helper_redaction.py
    │   ├── audit/test_decorator.py
    │   ├── versioning/test_publish.py
    │   └── snapshot/test_builder.py
    ├── integration/
    │   ├── test_audit_privileges.py            # SC-002
    │   ├── test_audit_rls.py                   # SC-007
    │   ├── test_versioning_overlap.py          # SC-004
    │   ├── test_snapshot_recompute.py          # SC-003
    │   └── test_audit_log_endpoint.py          # SC-006
    ├── perf/
    │   └── test_audit_throughput.py            # SC-005
    └── e2e/
        └── test_recompute_from_snapshot_flow.py

frontend/
├── app/
│   ├── components/
│   │   └── VersionBadge.vue                    # FR-012
│   ├── pages/
│   │   └── (none added; F32 owns the audit view UI)
│   └── composables/
│       └── useVersionBadge.ts                  # date/version formatting
└── tests/
    └── unit/
        └── VersionBadge.spec.ts
```

**Structure Decision**: Web-app split (already in place from F01). New backend modules grouped by concern (`audit/`, `versioning/`, `snapshot/`) rather than scattered into `services/` to keep the cross-cutting nature of these primitives obvious. One Vue display component on the frontend; no new page (F32 will compose the audit view).

## Complexity Tracking

No constitutional violations to justify.
