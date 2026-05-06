# Implementation Plan: Agent LangGraph Core (orchestration backend câblée)

**Branch**: `053-agent-langgraph-core` | **Date**: 2026-05-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/053-agent-langgraph-core/spec.md`

## Summary

F53 transforme le proxy LLM brut de `backend/app/chat/llm_stream.py` en un **agent LangGraph effectif** : machine d'état (StateGraph) avec 8 nœuds (`route` → `build_context` → `recall_memory` → `select_tools` → `call_llm` → `validate_payload` → `dispatch_tool` → `compose_response`) qui orchestre tous les composants déjà livrés (F14 classifier/validator/retry, F15/16/17 tools, F18 memory, F19 skills loader, F21 skills MVP). L'endpoint `POST /messages` bascule vers `run_agent(...)` quand `LLM_AGENT_MODE='langgraph'` (défaut), conservant un fallback `raw` instantané pour rollback opérationnel. Persistance de l'état via `PostgresSaver` (LangGraph) avec `thread_id` composite `"{account_id}:{conv_uuid}"` pour l'isolation tenant. Tracing via deux nouvelles tables RLS-protégées : `agent_run` (un par tour) + `agent_run_step` (un par nœud). Concurrence sur même thread gérée par `pg_advisory_xact_lock`. Tests E2E mixtes : pytest backend (httpx + ASGI) dominants + 2 specs Playwright pour la chaîne UI.

## Technical Context

**Language/Version** : Python 3.12+ (backend FastAPI), TypeScript 5.x (frontend Nuxt 4 — concerné uniquement par les 2 specs Playwright)
**Primary Dependencies** : FastAPI, SQLAlchemy 2.x, Pydantic v2, **NEW** `langgraph^0.2`, `langchain-core^0.3`, `langchain-openai^0.2`, `langgraph-checkpoint-postgres^2.0`. Réutilise `app.orchestrator.*` (F14), `app.chat.*` (F13), `app.skills.*` (F19), `app.memory.*` (F18), `app.audit.*` (F04), `app.tools.*` registry (F15-17).
**Storage** : PostgreSQL 16 + pgvector (image `pgvector/pgvector:pg16`). 3 tables nouvelles : `agent_run`, `agent_run_step` (versionnées Alembic), `langgraph_*` (gérées par `PostgresSaver.setup()` au boot, hors Alembic).
**Testing** : `pytest` + `pytest-asyncio` + `pytest-cov` (backend), `httpx.AsyncClient` (E2E ASGI), `playwright/test` (UI). Fixture `fakellm` pour mock LangChain. Coverage gate `fail_under=80` global, ≥85 % spécifique sur `backend/app/agent/`.
**Target Platform** : backend Linux/macOS (uvicorn .venv local en dev, conteneur en prod EU/Afrique de l'Ouest), frontend Nuxt 4 SPA. Pas de USA.
**Project Type** : web (backend + frontend déjà en place, F53 ajoute un module backend `app/agent/` + 2 tests Playwright frontend).
**Performance Goals** : pipeline agent (hors LLM principal) < 500 ms p95 (NFR-001), boot complet (compile graph + setup checkpointer) < 5 s (SC-004), `/health/agent` < 100 ms.
**Constraints** : mémoire RAM par exécution < 50 MB (NFR-003), `mypy --strict` sans `# type: ignore` (NFR-004), pas de hardcode endpoint/model/tool (NFR-007), RLS strict (NFR-006).
**Scale/Scope** : ~50-200 PME actives MVP, 5-20 messages/utilisateur/jour, ~1000-5000 tours d'agent/jour. 18 FR + 7 NFR + 10 SC.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | F53 inclut FR-016 : tout chiffre ESG/financier MUST être lié à un `Source.status='verified'` via `cite_source` ; le validator MUST rejeter sinon. F56 finit l'enforcement (post-validation + bandeau). | ✅ |
| P2 | Multi-tenant RLS | `agent_run` et `agent_run_step` portent `account_id` + RLS (FR-011). FR-013 : RLS via `app.current_account_id` GUC, cross-tenant → 404. `thread_id` composite `{account_id}:{uuid}` pour isoler les checkpoints LangGraph. SC-005 = test 50 cas cross-tenant. | ✅ |
| P3 | Audit log append-only | `agent_run` et `agent_run_step` sont append-only (pas d'UPDATE/DELETE en applicatif, REVOKE migration). Les tools de mutation déclenchent `audit_log` via dispatcher (FR-007 b). | ✅ |
| P4 | Versioning + snapshot candidatures | F53 ne crée ni ne modifie de référentiel ; les schémas Pydantic des tools restent dans la version exposée par F19 (skills). Pas de candidature gérée directement par F53. | ✅ |
| P5 | Money typé | F53 ne calcule aucun montant ; les tools de mutation (F17) reçoivent du `Money={amount, currency}` sérialisé Pydantic. Le validateur F14 le contrôle déjà. | ✅ |
| P6 | Pivot Indicateur unique | F53 n'écrit pas d'indicateurs directement ; via `update_*`/`create_*` tools F17, qui respectent ce pivot. | ✅ |
| P7 | Plateforme fermée aux intermédiaires | F53 sert uniquement les rôles `PME` + `Admin` (auth existante). Aucun nouveau rôle introduit. | ✅ |
| P8 | Édition manuelle + sync LLM | Tout champ écrit par l'agent reste manuellement éditable côté Profil/Projets (F11/F12). EventBus front (F41) pousse les mutations LLM. Édition manuelle invalide la mémoire (F18). | ✅ |
| P9 | Tool-use LLM fiable | C'est l'épine dorsale de F53 : classifier (F14) → tool-subset ≤10 (FR-015 LLM_AGENT_MAX_TOOLS=10) → validate Pydantic strict (F14) → max 2 retries (FR-006 LLM_AGENT_MAX_RETRIES=2) → fallback texte. Max 1-2 skills/tour (FR-017). Eval gating ≥50 cas → délégué F58. | ✅ |
| P10 | UX bottom sheet | Les tools `ask_*` et `show_form` sont dispatchés via SSE event `tool_invoke` (FR-007 a) → bottom sheet géré par F39/F41. Pas d'inputs inline. Côté F53, c'est un dispatcher pur. | ✅ |

### Contraintes techniques (rappel)

- ✅ Stack respectée : FastAPI + Python 3.12 (backend), Nuxt 4 (frontend), Postgres + pgvector. LLM via OpenRouter (`LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL` settings).
- ✅ Dev local : backend `.venv`, Postgres dockerisé seul, frontend `pnpm dev`.
- ✅ Hébergement EU/UEMOA : LangGraph et `langgraph-checkpoint-postgres` sont des libs OSS exécutées sur le backend hébergé en EU/Afrique de l'Ouest. Aucun appel sortant vers US (LLM via OpenRouter EU endpoint si applicable).
- ✅ RGPD + 2013-450 + UEMOA 20/2010 : les checkpoints contiennent du contenu utilisateur (messages) → restent en Postgres local au déploiement, pas exfiltrés. Audit log respecte le sourcing.
- ✅ Langue : messages assistant et erreurs MUST être en FR par défaut (system prompt F54). Le code est en EN.

**Verdict** : ✅ Tous les gates P1–P10 passent. Pas de violation à justifier.

## Project Structure

### Documentation (this feature)

```text
specs/053-agent-langgraph-core/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (SSE events + healthcheck OpenAPI)
│   ├── sse-events.md
│   └── healthcheck-agent.openapi.yaml
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

Web application layout (déjà en place) :

```text
backend/
├── app/
│   ├── agent/                          # NEW (F53 racine, étendu par F54-F58)
│   │   ├── __init__.py                 # exports compile_agent_graph, run_agent
│   │   ├── state.py                    # AgentState Pydantic v2 + types
│   │   ├── graph.py                    # build_graph() StateGraph
│   │   ├── runner.py                   # run_agent(...) AsyncIterator[SseEvent]
│   │   ├── llm_factory.py              # ChatOpenAI builder
│   │   ├── tool_factory.py             # ToolDef → StructuredTool
│   │   ├── checkpointer.py             # PostgresSaver wrapper + thread_id composite
│   │   ├── tracing.py                  # agent_run + agent_run_step writer
│   │   ├── concurrency.py              # pg_advisory_xact_lock helper
│   │   ├── sse_bridge.py               # LangGraph events → SSE protocol (F55 polish)
│   │   ├── models.py                   # SQLAlchemy AgentRun + AgentRunStep
│   │   ├── repository.py               # CRUD append-only run/step
│   │   ├── api.py                      # GET /health/agent
│   │   └── nodes/                      # un fichier par nœud, async pure
│   │       ├── __init__.py
│   │       ├── route.py                # intent classifier
│   │       ├── build_context.py        # ctx_full / ctx_min (F54 polish)
│   │       ├── recall_memory.py        # delegates to chat.memory
│   │       ├── select_tools.py         # tool_selector
│   │       ├── call_llm.py             # ChatOpenAI.astream
│   │       ├── validate_payload.py     # Pydantic strict + retry
│   │       ├── dispatch_tool.py        # 3 voies (SSE / DB / re-call)
│   │       └── compose_response.py     # final text + persist via chat.service
│   ├── chat/                           # MODIF (F13)
│   │   ├── api.py                      # MODIF : branchement langgraph/raw
│   │   └── llm_stream.py               # PRÉSERVÉ (mode raw fallback)
│   ├── config.py                       # MODIF : LLM_AGENT_* settings
│   └── main.py                         # MODIF : startup compile + register agent router
├── alembic/
│   ├── versions/
│   │   └── 0XXX_agent_run_steps.py     # NEW — agent_run + agent_run_step uniquement
│   └── README.md                       # CRÉER si absent — coexistence Alembic / LangGraph
├── tests/
│   ├── unit/
│   │   ├── test_agent_state.py
│   │   ├── test_agent_llm_factory.py
│   │   ├── test_agent_tool_factory.py
│   │   ├── test_agent_concurrency.py
│   │   ├── test_agent_nodes_route.py
│   │   ├── test_agent_nodes_validate.py
│   │   ├── test_agent_nodes_dispatch.py
│   │   └── test_agent_nodes_compose.py
│   ├── integration/
│   │   ├── test_agent_graph.py         # FR-014 — couverture nodes
│   │   ├── test_agent_cross_tenant.py  # SC-005 — RLS isolation
│   │   ├── test_agent_cancellation.py  # SC-007 — SSE disconnect
│   │   ├── test_agent_checkpoint.py    # SC-010 — resume after restart
│   │   ├── test_agent_concurrency.py   # advisory lock
│   │   ├── test_agent_health.py        # FR-015
│   │   ├── test_agent_modes.py         # SC-008 — langgraph/raw rollback
│   │   └── test_agent_tracing.py       # FR-011 — runs/steps rows
│   ├── e2e/                            # backend E2E (httpx + ASGI)
│   │   ├── test_agent_e2e_create_project.py   # SC-001
│   │   └── test_agent_e2e_analysis_sourced.py # SC-002
│   └── conftest.py                     # MODIF : fakellm, fakegraph, fakecheckpointer
└── pyproject.toml                      # MODIF : pin langgraph, langchain-*

frontend/
└── tests/
    └── e2e/
        ├── agent-chat-create-project.spec.ts   # Playwright SC-001 (chaîne UI)
        └── agent-chat-cancellation.spec.ts     # Playwright SC-007 (Stop button)
```

**Structure Decision** : application web existante. F53 ajoute un module backend autonome `backend/app/agent/` (architecture domain-per-feature constitutionnelle), modifie 3 points existants (`config.py`, `chat/api.py`, `main.py`), ajoute 1 migration Alembic, ne touche pas au frontend hors 2 specs Playwright. La structure des tests respecte la convention `unit / integration / e2e` du projet.

## Phase 0 — Research output

Cf. [research.md](./research.md). Toutes les NEEDS CLARIFICATION sont déjà résolues (5 clarifications dans le spec). Reste à formaliser les choix techniques précis (versions de pin, patterns LangGraph idiomatic, schéma SQL exact des nouvelles tables, format des SSE events).

## Phase 1 — Design output

- [data-model.md](./data-model.md) — schéma `agent_run`, `agent_run_step`, AgentState typing, format `thread_id` composite
- [contracts/sse-events.md](./contracts/sse-events.md) — protocole SSE events (token, tool_invoke, mutation, validation_retry, error, done)
- [contracts/healthcheck-agent.openapi.yaml](./contracts/healthcheck-agent.openapi.yaml) — `GET /health/agent` schema
- [quickstart.md](./quickstart.md) — comment démarrer le backend en mode langgraph, comment basculer en raw, comment lancer la suite de tests

## Constitution Check (post-design)

Tous les gates P1–P10 restent ✅ après design (cf. tableau ci-dessus). Aucune violation à inscrire dans `Complexity Tracking`. Le module `backend/app/agent/` est autonome (pas de couplage cross-domain hormis appels explicites aux services F13/14/17/18/19), respecte la limite ~200-400 lignes par fichier (un nœud par fichier), reste stricly typé (NFR-004 mypy --strict).

## Complexity Tracking

> Aucune violation des gates constitutionnels. Section vide.
