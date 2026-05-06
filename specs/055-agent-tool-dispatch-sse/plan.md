# Implementation Plan: Agent Tool Dispatch & SSE Bridge

**Branch**: `055-agent-tool-dispatch-sse` | **Date**: 2026-05-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/055-agent-tool-dispatch-sse/spec.md`

## Summary

F55 — Tool Dispatch & SSE Bridge — livre le **dispatcher** central côté backend qui exécute chaque tool call validé selon sa catégorie (`ASK`/`SHOW`/`MUTATION`/`READ`), avec audit log automatique, rate limit per-tenant, idempotence par hash, confirmation des mutations destructives, mode dry_run admin et hooks pre/post handler. Le **runner** F53 transforme les events LangGraph en frames SSE (`text_delta`, `tool_invoke`, `mutation`, `tool_call_completed`, `error`, `message_done`) consommés côté frontend par `useChatStream` et le store Pinia `chat`. Une migration Alembic ajoute `tool_call_id` + `agent_run_id` (NULLABLE FK) sur `audit_log` et `idempotency_key` + `agent_run_id` + `dispatch_result_kind` sur `tool_call_log`.

Approche technique : étendre `app/agent/nodes/dispatch_tool.py` (squelette F53) en ajoutant la couche `MutationCtx`, le décorateur `@mutation_handler`, le rate limiter pluggable (in-memory dev / Redis prod) avec fail-safe, l'idempotence DB et le confirmation flow ; étendre `app/agent/sse_bridge.py` (déjà partiel F53) pour les events `tool_call_completed`, `text_delta`, `dry_run:` prefix ; brancher la chaîne dans `app/chat/llm_stream.py` et exposer les nouveaux events dans `frontend/app/composables/useChatStream.ts` + `frontend/app/stores/chat.ts`.

## Technical Context

**Language/Version**: Python 3.12 (backend, FastAPI), TypeScript 5.x (frontend, Nuxt 4 / Vue 3 Composition API)
**Primary Dependencies**: FastAPI, SQLAlchemy 2 + Alembic, LangChain + LangGraph, Pydantic v2 (`extra='forbid'`), Voyage AI client, OpenRouter (`minimax-m2.7`), httpx (tests), pytest + pytest-asyncio + pytest-cov, Nuxt 4 + Pinia + Tailwind v4 + chart.js, Playwright
**Storage**: PostgreSQL + pgvector (extension `audit_log` + `tool_call_log`) ; pas de Redis en dev (in-memory bounded LRU acceptable single-worker, Redis requis multi-worker prod)
**Testing**: pytest (backend, markers unit/integration/perf, coverage `fail_under=80` ; ≥ 90% sur dispatcher/mutation_ctx/rate_limiter), Vitest (frontend), Playwright (E2E UI)
**Target Platform**: Linux EU/Afrique de l'Ouest (RGPD + UEMOA 20/2010 + loi ivoirienne 2013-450) ; pas de hosting US
**Project Type**: web — backend FastAPI + frontend Nuxt 4 (extension Chrome MV3 hors-scope F55)
**Performance Goals**: dispatch ASK/SHOW < 5 ms, MUTATION < 100 ms p95, READ < 500 ms p95 ; SSE flush par event sans buffering
**Constraints**: ≤ 10 tool calls par tour (hard cap), retry max 2 (P9), rate limit per-tenant configurable, idempotence DB-backed UNIQUE per `(account_id, idempotency_key)`, fail-safe rate limiter (NFR-007), audit log append-only même transaction que la mutation business (P3)
**Scale/Scope**: 1 backend worker dev + multi-worker prod ; ~12 tools mutation à enregistrer (update_company_profile, create_project, update_project, delete_project, create_candidature, update_candidature_status, attach_document, recompute_score, generate_attestation, revoke_attestation, generate_dossier, recompute_carbon) ; ~3 tools READ (cite_source, search_source, recall_history) ; ~20 tools ASK/SHOW (existants F15/F16)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Les payloads `show_*` non sourcés sont-ils rejetés en amont par le validateur F14 ? Les rapports finaux conservent-ils la chaîne de citations ? | ✅ — F55 ne touche pas au validateur P1 ; tout payload non sourcé est déjà rejeté avant dispatch (vérifié par US2 scénario 3) |
| P2 | Multi-tenant RLS | Toute nouvelle table porte-t-elle account_id ? Cross-tenant retourne-t-il 404 ? | ✅ — pas de nouvelle table métier (audit_log et tool_call_log existent déjà avec account_id + RLS) ; ajouts de colonnes seulement, RLS héritée. US1 scénario 3 + NFR-005 garantissent l'isolation |
| P3 | Audit log append-only | Toute mutation est-elle journalisée avec source_of_change ∈ {manual, llm, import, admin} ? | ✅ — F55 garantit `source_of_change='llm'` automatique sur chaque mutation dispatchée + tool_call_id + agent_run_id (FR-009). audit_log reste append-only (INSERT only) |
| P4 | Versioning + snapshot candidatures | Référentiels/critères versionnés ? Candidatures portent snapshot_json ? | ✅ — F55 ne crée aucun référentiel ; les handlers de mutation respectent la versioning side-effect (cf. F17) |
| P5 | Money typé | Les montants sont-ils Decimal + ISO 4217 ? | ✅ — les tool schemas mutation héritent du typage Money de F17 ; F55 ne manipule pas directement de montant brut |
| P6 | Pivot Indicateur unique | Les données ESG passent-elles par Indicateur ? | ✅ — F55 dispatch tools, pas de schéma ESG nouveau. update_indicator sera un mutation existant |
| P7 | Plateforme fermée aux intermédiaires | Pas de rôle Intermediaire ? Sorties via attestation Ed25519 ? | ✅ — F55 ne crée aucun nouveau rôle. `revoke_attestation` reste un tool mutation interne PME, pas un push intermédiaire |
| P8 | Édition manuelle + sync LLM | Tout champ LLM modifiable manuellement ? Mutation manuelle invalide contexte LLM ? | ✅ — l'EventBus F55 publie `entity_updated` avec `source='llm'` pour ne PAS retrigger une mutation chat (FR-013 anti-loop). Les pages frontend invalidant le cache LLM vivent côté F08 |
| P9 | Tool-use LLM fiable | Nouveaux tools nommés/documentés/Pydantic strict ? Retry ≤ 2 ? Eval gating planifié ? | ✅ — F55 n'ajoute pas de tool, il enregistre des handlers. La validation Pydantic strict (extra='forbid') héritée de F14 est respectée. Retry max 2 = state F53. Eval gating reste F58 |
| P10 | UX bottom sheet | Composants interactifs en bottom sheet ? Bouton "Répondre librement" ? | ✅ — `tool_invoke` (ASK) déclenche `useChatBottomSheet().open` côté frontend (FR-018). La bulle assistant reste display-only (FR-019). Bouton "Répondre librement" géré par F39 |

**Verdict** : 10/10 gates ✅. Pas de violation. Pas de Complexity Tracking nécessaire.

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ; LLM via OpenRouter `minimax-m2.7` ; embeddings Voyage `voyage-3.5` (1024 dim).
- Dev local : backend en `.venv`, Postgres seul service dockerisé.
- Hosting prod : Europe ou Afrique de l'Ouest uniquement.
- Conformité : RGPD + loi ivoirienne 2013-450 + UEMOA 20/2010.
- Langue : français par défaut.

## Project Structure

### Documentation (this feature)

```text
specs/055-agent-tool-dispatch-sse/
├── plan.md              # This file (/speckit-plan output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (sse-events.md, dispatcher-api.md)
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── agent/
│   │   ├── dispatcher.py             # NEW — dispatch central + hooks pre/post
│   │   ├── mutation_ctx.py           # NEW — MutationCtx immuable
│   │   ├── mutation_handlers.py      # NEW — registry @mutation_handler + handlers F17
│   │   ├── rate_limit.py             # NEW — interface + InMemoryStore + RedisStore
│   │   ├── idempotency.py            # NEW — hash + DB lookup tool_call_log
│   │   ├── confirmation.py           # NEW — pending_confirmation flow
│   │   ├── sse.py                    # NEW — format_event helper
│   │   ├── nodes/
│   │   │   └── dispatch_tool.py      # ENRICHIE — câble dispatcher.py
│   │   ├── sse_bridge.py             # ENRICHIE — text_delta, tool_call_completed, dry_run prefix
│   │   ├── runner.py                 # PATCHED — astream_events v2 → SSE frames
│   │   └── state.py                  # PATCHED — ToolCategory, dry_run flag, max tool calls per turn
│   ├── chat/
│   │   ├── api.py                    # PATCHED — endpoint stream branche F55
│   │   └── llm_stream.py             # PATCHED — utilise dispatch + sse_bridge
│   ├── orchestrator/
│   │   ├── tool_registry.py          # PATCHED — champ category requis (fail-fast)
│   │   └── schemas.py                # PATCHED — ToolCategory enum
│   └── audit/                        # héritée — append_diff(.., tool_call_id, agent_run_id)
├── alembic/
│   └── versions/
│       └── XXXX_f55_audit_tool_call_extensions.py  # NEW migration
└── tests/
    ├── unit/
    │   ├── test_dispatcher_routing.py        # NEW
    │   ├── test_mutation_ctx.py              # NEW
    │   ├── test_rate_limit_inmemory.py       # NEW
    │   ├── test_idempotency.py               # NEW
    │   ├── test_confirmation_flow.py         # NEW
    │   ├── test_sse_format.py                # NEW
    │   └── test_dispatcher_hooks.py          # NEW
    ├── integration/
    │   ├── test_dispatch_ask_show.py         # NEW — catégorie ASK/SHOW e2e
    │   ├── test_dispatch_mutation_audit.py   # NEW — UPDATE + audit_log dans même transaction
    │   ├── test_dispatch_read_reinject.py    # NEW — recall_history → ToolMessage
    │   ├── test_dispatch_rls_isolation.py    # NEW — cross-tenant 404
    │   ├── test_dispatch_rate_limit_31.py    # NEW — 30 succès + 1 rate_limited
    │   ├── test_dispatch_idempotency_replay.py # NEW — reconnexion SSE
    │   ├── test_dispatch_confirmation_yesno.py # NEW — delete_project flow
    │   ├── test_dispatch_dry_run_admin.py    # NEW — dry_run prefix
    │   └── test_boot_fail_fast.py            # NEW — handler manquant fail boot
    └── e2e/
        └── test_chat_mutation_e2e.py         # NEW — pytest+httpx ASGI complet

frontend/
├── app/
│   ├── composables/
│   │   ├── useChatStream.ts          # PATCHED — handle tool_invoke, mutation, tool_call_completed, error, message_done
│   │   └── useChatToolBridge.ts      # NEW — pont ASK→bottom sheet, SHOW→viz inline
│   ├── stores/
│   │   └── chat.ts                   # PATCHED — pending tool calls, dry_run state, mutation refresh
│   └── components/
│       └── chat/
│           ├── DryRunBanner.vue      # NEW — bandeau simulation
│           └── MessageBubble.vue     # PATCHED — render viz inline (SHOW)
└── tests/
    ├── unit/
    │   ├── useChatStream.test.ts     # NEW
    │   ├── useChatToolBridge.test.ts # NEW
    │   └── stores/chat.test.ts       # NEW
    └── e2e/
        ├── chat-bottom-sheet.spec.ts # NEW — Playwright ASK flow
        └── chat-mutation-sync.spec.ts # NEW — Playwright mutation→Profil refresh
```

**Structure Decision** : web (option 2) — backend Python `.venv` séparé du frontend Nuxt. Les modules sont tous sous `backend/app/agent/` (dispatcher, mutation_ctx, rate_limit, etc.) afin de centraliser la couche agent et faciliter le code review. Une migration Alembic unique englobe les deux extensions de table (audit_log + tool_call_log) pour minimiser les churns.

## Complexity Tracking

Aucune violation constitutionnelle ; section non utilisée.
