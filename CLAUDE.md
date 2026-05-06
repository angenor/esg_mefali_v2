# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
specs/058-agent-guardrails-eval/plan.md
<!-- SPECKIT END -->

The Spec Kit "current feature" is tracked in `.specify/feature.json` (`feature_directory`). When unsure which feature is active, read that file first — it points to the spec/plan/tasks under `specs/`.

## Project

ESG Mefali v2 — plateforme conversationnelle IA de finance verte pour PME ouest-africaines (FR par défaut). Stack imposée par la constitution (`.specify/memory/constitution.md`) : **FastAPI + Python 3.12+**, **Nuxt 4 + Pinia + Tailwind v4**, **PostgreSQL + pgvector** (RLS), LLM via OpenRouter (`minimax-m2.7` par défaut), embeddings **Voyage AI `voyage-3.5` (1024 dim)**.

L'hébergement de production est restreint à l'**Europe ou l'Afrique de l'Ouest** (RGPD + UEMOA 20/2010 + loi ivoirienne 2013-450). Pas de déploiement US.

## Commands (Makefile is the canonical reference)

```bash
make setup            # backend .venv + pip install + frontend pnpm install
make db-up            # postgres dockerisé (seul service docker en dev)
make db-reset         # down -v + up + alembic upgrade head
make migrate          # alembic upgrade head (depuis backend/.venv)
make backend          # uvicorn app.main:app --reload --port 8010
make frontend         # nuxt dev (port 3001)
make test             # backend (pytest --cov) + frontend (vitest run)
make lint             # ruff check backend + eslint frontend
```

Backend uses a local `.venv` in `backend/` — **pas de conteneur backend en dev**. Postgres est le **seul** service Docker. Run backend commands after `cd backend && source .venv/bin/activate`.

### Démarrer les serveurs (3 terminaux)

```bash
# Terminal 1 — Postgres (pgvector, port 5432)
make db-up
docker compose ps                                  # vérifier "healthy"

# Terminal 2 — Backend FastAPI (port 8010)
make backend
# équivalent manuel : uvicorn app.main:app --reload --port 8010
# cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8010
curl http://localhost:8010/health                  # → {"status":"ok","db":"ok"}

# Terminal 3 — Frontend Nuxt (port 3001)
make frontend
# équivalent manuel : cd frontend && pnpm dev --port 3001
# → http://localhost:3001  (apiBase défaut = http://localhost:8010)
```

Premier démarrage uniquement : `cp .env.example .env` (renseigner `DB_PASSWORD`, `LLM_*`, `JWT_SECRET`, `VOYAGE_API_KEY`, `REPLICATE_API_TOKEN`) puis `make setup` puis `make migrate`.

Si le port 8010 est déjà pris : `uvicorn app.main:app --reload --port <autre>` côté backend ET `NUXT_PUBLIC_API_BASE=http://localhost:<autre> pnpm dev` côté frontend (les deux doivent pointer sur le même port).

Arrêt : `Ctrl+C` dans chaque terminal ; `make db-down` pour stopper Postgres (les données persistent dans le volume).

### Single-test invocation

```bash
# Backend (pytest)
cd backend && source .venv/bin/activate
pytest tests/path/to/test_file.py::test_name -v
pytest -m integration              # markers : unit | integration | perf
pytest --cov=app --cov-report=term-missing

# Frontend (vitest)
cd frontend && pnpm vitest run path/to/file.test.ts
```

Coverage gate is `fail_under = 80` (`backend/pyproject.toml`). Ruff config (`select = E,F,W,I,B,UP`, `line-length = 100`) and pytest markers are also there.

## Architecture (big picture)

### Backend layout (`backend/app/`)

Each business domain is a self-contained package; the **domain-per-feature** layout is the architectural pattern. Cross-cutting modules:

- `main.py` — FastAPI app, middleware order: `RequestIdMiddleware` → `AuthSessionMiddleware` → CORS, then SlowAPI rate limiter. All routers are mounted here — when adding a feature, register its router in `main.py`.
- `db.py` — SQLAlchemy session and the per-request hook that sets `app.current_account_id` (Postgres GUC) used by RLS policies. **Never query business tables without this set** (constitution P2).
- `config.py` — Pydantic settings; **must fail fast** if required env vars are missing.
- `llm_client.py` / `embeddings_client.py` — single integration point for the OpenRouter LLM (`LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL`) and Voyage embeddings (`VOYAGE_API_KEY`, 1024-dim vectors). **Never hard-code endpoints or models** elsewhere.
- `core/`, `middleware/`, `decorators/`, `utils/` — shared infrastructure.
- `audit/`, `versioning/`, `snapshot/`, `auth/`, `users/` — implement constitutional invariants (audit append-only, referential versioning, candidature snapshot_json, RLS-aware auth).

Domain packages (`candidatures/`, `chat/`, `scoring/`, `matching/`, `dossier/`, `simulation/`, `carbon/`, `credit/`, `attestations/`, `action_plan/`, `dashboard/`, `rapports/`, `entreprise/`, `projets/`, `catalog/`, `extension/`, `eval/`, `skills/`, `orchestrator/`, `notifications/`, `email/`, `storage/`, `prompts/`, `llm/`) typically expose `router.py` (or `api.py`) + service code + Pydantic schemas. The `admin/` package hosts admin/CRUD/publish/search/stats routers separately.

### LLM tool-use (constitution P9 — non-negotiable)

The orchestration is a strict pipeline: classifier → tool-subset selector (≤10 tools) → LLM with filtered tools → **strict Pydantic v2 validation** (`extra='forbid'`, closed enums, bounds) → max 2 retries on structured error → text fallback. Each tool MUST have docstring "use when" / "don't use when". A turn must execute at most 1–2 skills. Code lives under `app/llm/`, `app/orchestrator/`, `app/skills/`, `app/prompts/`.

Skills are subject to **eval gating** (≥50 cases golden set) before publication — see `backend/tests/llm_eval/` and `app/eval/`.

### Frontend (`frontend/app/`)

Nuxt 4 (Composition API) + Pinia + Tailwind v4 (`@import tailwindcss`) + chart.js + mermaid + Leaflet + gsap + driver.js + toast-ui editor + `@langchain/langgraph` (front-side LLM orchestration) + nuxt-security. Routes in `pages/`, composables in `composables/` (e.g., `useHealth()`), styles in `assets/css/main.css`.

**UX rule (constitution P10)**: any interactive input (radios, checkboxes, file upload, forms, sliders, datepickers) MUST live in a **bottom sheet** animated with gsap, never inline in an LLM bubble. The LLM bubble is display-only (text, KPI, charts, mermaid, tables). A "Répondre librement" button must always switch to free text input.

### Database & migrations

- `backend/alembic/` — single migration chain. The initial migration `0001` provisions the 18-table schema. `alembic upgrade head` from `backend/.venv` (reads `../.env`).
- Every business table MUST have `account_id UUID NOT NULL` and an RLS policy `USING (account_id = current_setting('app.current_account_id')::uuid)`. Cross-tenant access returns **404, not 403** (P2).
- Audit table: applicative roles have `INSERT` only — `UPDATE`/`DELETE` are revoked (P3). Any mutation (human, LLM, import, admin) writes `{user_id, account_id, ts, entity, field, old, new, source_of_change}`.
- Referential entities (`Référentiel`, `Indicateur`, `Critère`, `Formule`, `Seuil`, `Facteur émission`, skill templates) carry `version` + `valid_from` + `valid_to` and are **never overwritten** (P4). Candidatures store an immutable `snapshot_json` reproducible 5 years out.

### Browser extension (`extension/`)

Chrome MV3 (manifest, background/content/popup) — used by features 033–034 (detection/prefill, guidage/suivi/notifications) and **F52** (sidepanel + push notifications) to surface ESG Mefali on third-party platforms. Backend endpoints under `app/extension/` and `app/api/routes/` serve it.

F52 ajoute :

- `extension/sidepanel/` — bundle Vite Vue 3 standalone (3 vues : `candidatures`, `offers`, `chat`), `chrome.sidePanel` API, < 200 kB gzip (mesuré ~32 kB). Tests Vitest dans `extension/sidepanel/__tests__/`.
- `extension/background-helpers/notifications.ts` — wrapper testable autour de `chrome.notifications` (utilisé par `background.js`, `kind=deadline_j_minus_1` → notification système ; clic ouvre la candidature dans un nouvel onglet).
- `extension/background.js` — heartbeat `POST /me/extension/ping` toutes les 30 min, validation `sender.tab.url` contre catalogue F33, fetch `/me/extension/sidepanel-context`, EventSource SSE `/me/notifications/stream` pour le push notif.
- Build : `pnpm --dir extension build:sidepanel` (sortie `extension/dist/sidepanel/`, garde-fou `scripts/check-bundle-size.mjs`).

## Constitutional invariants (`.specify/memory/constitution.md`)

The 10 non-negotiable principles MUST be respected on every feature. The most operationally relevant when writing code:

- **P1 Sourcing** — every ESG/financial assertion needs a `source_id` pointing to a `verified` `Source`. Tools without a prior `cite_source` call MUST be rejected by the validator. PDF reports auto-append a "Sources et références" annex.
- **P5 Money typed** — all monetary values are `{amount: Decimal, currency: ISO 4217}`. **Never `float`**. FCFA-EUR peg is fixed at `655.957` (sourced). USD via daily snapshot in `fx_rate`.
- **P6 Single Indicator pivot** — ESG data is stored as `Indicateur` values only; never duplicated per E/S/G axis or per referential. The E/S/G grid is a view, not stored.
- **P7 No intermediary roles** — only `PME` and `Admin` roles exist. Sharing to a fund/bank goes through a signed (Ed25519) verifiable attestation with public read-only `/verify/{id}` page. No webhooks/push to intermediaries.
- **P8 Bidirectional sync** — every LLM-written field MUST be manually editable; manual edits invalidate LLM context immediately; LLM mutations propagate to UI via EventBus/SSE. DB is the source of truth, never the LLM context.

## Workflow

Features follow Spec Kit: `/speckit.specify` → `/speckit.clarify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.implement`. The 35-feature backlog is in `docs_et_brouillons/features/00-INDEX.md` with phasing/dependencies — **don't start a feature whose dependency is still `draft`**. Each spec must list its **hors-scope MVP** explicitly.

## Language

Code identifiers can be English; **user-facing strings, errors, and reports default to French**. English is allowed only for candidature dossiers when the offer's `accepted_languages` includes `'en'`. Local languages (Wolof, Bambara, …) are post-MVP.

## Troubleshooting

| Symptôme | Solution |
|---|---|
| Port 5432 in use | Set `POSTGRES_PORT=5433` in `.env` and recreate compose |
| `/health` → 503 | `docker compose ps`; check `DB_PASSWORD` |
| Frontend "Backend indisponible" | uvicorn down or wrong `NUXT_PUBLIC_API_BASE` |
| `alembic` ne trouve pas la base | Run from `backend/` so `../.env` is loaded |
| `psycopg-binary` install fails | Python must be 3.12–3.14 |
