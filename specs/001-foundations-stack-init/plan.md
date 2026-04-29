# Implementation Plan: F01 — Initialisation Stack & Modèle Multi-tenant

**Branch**: `001-foundations-stack-init` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-foundations-stack-init/spec.md`

## Summary

Mettre en place l'infrastructure technique commune à 35+ features futures : structure de repo (backend FastAPI + frontend Nuxt 4), Postgres+pgvector dockerisée (seul service Docker), migrations Alembic créant le squelette du modèle conceptuel multi-tenant (18 entités), pattern Money (`_amount`+`_currency`+CHECK), colonne `embedding vector(1024)` pour pgvector, clients LLM (OpenRouter via SDK openai) et embeddings (Voyage AI) centralisés mais sans appel réel, page d'accueil Nuxt qui sonde `/health`, README documentant le démarrage en < 10 min.

## Technical Context

**Language/Version**: Python 3.12+ (backend, dans `.venv`) ; Node 20+ (frontend, via pnpm)

**Primary Dependencies**:
- Backend : FastAPI, uvicorn[standard], SQLAlchemy 2.x, Alembic, psycopg[binary], pydantic v2, pydantic-settings, python-dotenv, openai (SDK compatible OpenRouter), httpx, langgraph, langchain
- Frontend : Nuxt 4, Pinia (@pinia/nuxt), TailwindCSS v4, chart.js, mermaid, leaflet, gsap, driver.js, @fortawesome/fontawesome-svg-core + icons + vue-fontawesome, @toast-ui/editor, @langchain/langgraph

**Storage**: PostgreSQL 16 + extension `pgvector` + extension `pgcrypto` (pour `gen_random_uuid()`). RLS prévue F02.

**Testing**:
- Backend : pytest + pytest-asyncio + httpx (TestClient) + base Postgres dockerisée locale
- Frontend : vitest (unit). Playwright reporté post-F01.

**Target Platform**: Linux server (production Europe/Afrique de l'Ouest) ; Linux/macOS/WSL2 (dev local)

**Project Type**: Web application — `backend/` (FastAPI) + `frontend/` (Nuxt 4) + `docker-compose.yml` racine (Postgres seul)

**Performance Goals**:
- `alembic upgrade head` < 30 s (SC-002)
- `/health` < 200 ms p95 quand DB OK
- Démarrage uvicorn < 5 s

**Constraints**:
- Hébergement production Europe ou Afrique de l'Ouest uniquement (RGPD, UEMOA 20/2010, loi ivoirienne 2013-450)
- Aucun secret hard-codé (NFR-001)
- Postgres SEUL service Docker (FR-002)
- Backend en `.venv` local, PAS de Dockerfile backend en MVP

**Scale/Scope**: 18 tables initiales, ~25-30 fichiers backend, ~10-15 fichiers frontend de bootstrap.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

**Évaluation initiale (avant Phase 0)** :

| # | Principle | Gate question | Status |
|---|-----------|---------------|--------|
| P1 | Sourçage anti-hallucination | F01 ne crée AUCUNE donnée factuelle (chiffres, seuils, critères). Elle crée le SCHÉMA des tables Source/Indicateur/Critère. Le verrouillage `source_id NOT NULL` sera fait en F03. | ✅ pass (préparé) |
| P2 | Multi-tenant RLS | Toutes les tables métier (Entreprise, Projet, Candidature, ChatMessage, AuditLog, AccountUser) portent `account_id UUID NOT NULL` indexé. Activation RLS prévue F02. | ✅ pass (préparé pour F02) |
| P3 | Audit log append-only | Table `audit_log` créée avec colonnes (user_id, account_id, timestamp, entity_type, entity_id, field, old_value, new_value, source_of_change). Triggers et révocation UPDATE/DELETE en F04. | ✅ pass (préparé pour F04) |
| P4 | Versioning + snapshot | Toutes les tables portent `version INT NOT NULL DEFAULT 1`. Colonnes `valid_from`/`valid_to` créées sur Referentiel. `Candidature.snapshot_json JSONB` créé. | ✅ pass |
| P5 | Money typé | Tous les champs montants utilisent `_amount NUMERIC(18,2)` + `_currency CHAR(3)` + CHECK. Peg FCFA-EUR (655,957) documenté en commentaire. | ✅ pass |
| P6 | Pivot Indicateur unique | Table `Indicateur` créée comme pivot unique. Aucune table ne stocke de réponse PME indexée par axe E/S/G. | ✅ pass |
| P7 | Plateforme fermée aux intermédiaires | `AccountUser.role` sémantiquement {pme, admin}. Intermediaire/FondsSource sont entités CATALOGUE (pas comptes). | ✅ pass |
| P8 | Édition manuelle + sync LLM | F01 ne crée pas de surface fonctionnelle LLM. Table ChatMessage prête. | ✅ pass (n/a) |
| P9 | Tool-use LLM fiable | F01 ne crée AUCUN tool LLM. `llm_client.py` posé sans appel. | ✅ pass (n/a) |
| P10 | UX bottom sheet | F01 ne crée aucun composant interactif (page d'accueil sondant `/health`). | ✅ pass (n/a) |

**Verdict initial : ✅ Tous les gates passent. Aucun écart.**

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ✅
- Dev local : backend en `.venv`, Postgres seul service dockerisé, frontend `pnpm dev` ✅
- Hébergement production Europe / Afrique de l'Ouest uniquement (documenté README) ✅
- Conformité RGPD + 2013-450 + UEMOA 20/2010 : préparée structurellement (page Mes données livrée en F05)
- Langue : français par défaut (page Nuxt en français)

## Project Structure

### Documentation (this feature)

```text
specs/001-foundations-stack-init/
├── plan.md
├── spec.md
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── health.openapi.yaml
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (créé par /speckit-tasks)
```

### Source Code (repository root)

```text
.
├── docker-compose.yml              # Service postgres (pgvector/pgvector:pg16) UNIQUEMENT
├── README.md                       # Setup, dev, structure, hébergement Europe/AO
├── .env.example                    # Variables documentées (versionné)
├── .env                            # Local, gitignored
├── .gitignore                      # exclut .env, .venv, node_modules, __pycache__, dist, .nuxt
├── Makefile                        # Optionnel — alias des commandes setup
│
├── backend/
│   ├── .venv/                      # Local, gitignored
│   ├── requirements.txt
│   ├── pyproject.toml              # config ruff, pytest
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 0001_initial_schema.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app + GET /health
│   │   ├── config.py               # Settings pydantic, fail-fast
│   │   ├── db.py                   # Engine SQLAlchemy + session
│   │   ├── llm_client.py           # Client OpenRouter (sans appel en F01)
│   │   └── embeddings_client.py    # Client Voyage AI (sans appel en F01)
│   └── tests/
│       ├── conftest.py
│       ├── test_health.py
│       ├── test_config.py
│       └── test_migration_idempotency.py
│
└── frontend/
    ├── package.json
    ├── pnpm-lock.yaml
    ├── nuxt.config.ts              # tailwindcss v4, @pinia/nuxt
    ├── tailwind.config.ts
    ├── app.vue
    ├── pages/
    │   └── index.vue               # Appelle GET /health backend
    ├── plugins/
    │   ├── fontawesome.client.ts
    │   ├── chartjs.client.ts
    │   ├── mermaid.client.ts
    │   ├── leaflet.client.ts
    │   ├── gsap.client.ts
    │   └── driver.client.ts
    ├── composables/
    │   └── useHealth.ts
    └── assets/
        └── css/
            └── main.css            # @import "tailwindcss"
```

**Structure Decision**: Web application classique avec séparation `backend/` + `frontend/` à la racine, plus un `docker-compose.yml` racine ne contenant QUE le service Postgres (FR-002, P contraintes constitution). Le backend tourne dans son `.venv` (pas de Dockerfile MVP) ; le frontend via `pnpm dev` (pas de Dockerfile MVP). Conforme à la stack imposée par la constitution v1.0.0.

## Re-évaluation Constitution Check (post-design Phase 1)

| # | Principle | Status après design |
|---|-----------|---------------------|
| P1 | Sourçage anti-hallucination | ✅ data-model.md prévoit `source_id` sur Indicateur, Critere, FacteurEmission, DocumentRequis, Accreditation, Template (NULL en F01, NOT NULL en F03) |
| P2 | Multi-tenant RLS | ✅ data-model.md liste `account_id UUID NOT NULL` + index sur les 6 tables métier |
| P3 | Audit log append-only | ✅ Table `audit_log` créée avec source_of_change enum {manual, llm, import, admin} |
| P4 | Versioning + snapshot | ✅ Colonne `version` partout ; `valid_from`/`valid_to` sur Referentiel ; `snapshot_json JSONB` sur Candidature |
| P5 | Money typé | ✅ Toutes colonnes monétaires (taille_ca, montant_recherche, plafond, plancher) suivent le pattern + CHECK |
| P6 | Pivot Indicateur unique | ✅ Table Indicateur unique pivot |
| P7 | Plateforme fermée | ✅ AccountUser.role sémantiquement {pme, admin}, pas de rôle Intermediaire |
| P8 | Édition manuelle + sync LLM | ✅ n/a en F01 |
| P9 | Tool-use LLM fiable | ✅ n/a en F01 |
| P10 | UX bottom sheet | ✅ n/a en F01 |

**Verdict post-design : ✅ Tous les gates passent.**

## Complexity Tracking

> Aucune violation à justifier.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none)    | (none)     | (none)                               |
