# Implementation Plan: Agent Sourcing Enforcement (F56)

**Branch**: `056-agent-sourcing-enforcement` | **Date**: 2026-05-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/056-agent-sourcing-enforcement/spec.md`

## Summary

F56 cimente l'invariant constitutionnel **P1** (sourçage strict) en mécanisme structurel non contournable du runtime agent. Trois lignes de défense :

1. **Avant** : system prompt F54 instruit explicitement le LLM de citer ; F56 ajoute des exemples sourcés et la liste dynamique des sources verifiées disponibles.
2. **Pendant** : un nouveau package `app/agent/sourcing/` fournit le validateur ; le sélecteur de tools (F14, intégré F53) est patché pour **forcer** la présence de `cite_source`, `search_source`, `flag_unsourced` dans `state.available_tools` — ces 3 tools sont enregistrés en `TOOL_REGISTRY` (catégorie `READ` / `MUTATION`) et leurs handlers sont créés dans `app/agent/handlers/`.
3. **Après** : un détecteur regex+keyword (`sourcing/detector.py`, < 50 ms p95 / 2 KB) extrait les claims factuels du texte assistant ; le validateur (`sourcing/validator.py`) croise claims ↔ `cite_source` invoqués ; selon `LLM_AGENT_SOURCING_MODE` (`strict` | `permissive` | `off`), le nœud `compose_response` (F53) déclenche un retry sourcing unique, annote, ou laisse passer.

Side artifacts :

- migration `0035_f56_unsourced_flag_and_sourcing_columns` ajoutant la table `unsourced_flag` (RLS + audit append-only + UNIQUE partiel pour dédup), `agent_run.sourcing_status`, `chat_message.sources JSONB`, et un index pgvector sur `source.embedding` si absent.
- endpoint admin `GET /admin/agent/metrics/sourcing` (KPIs compliance).
- frontend chat F41 + extension sidepanel F52 consomment `payload.sources` SSE et rendent `<VizSourcePin>` (F40).
- F49 (rapports/attestations PDF) consommera `chat_message.sources` pour générer l'annexe — F56 livre la donnée, F49 le rendu.

## Technical Context

**Language/Version**: Python 3.12+ (backend), Node 22 + TypeScript 5+ (frontend Nuxt 4 + extension Vue 3)
**Primary Dependencies**:
- backend : FastAPI ≥ 0.115, SQLAlchemy 2.x, Pydantic v2 (`extra='forbid'`), LangGraph (F53 stack), pgvector, Voyage AI client (déjà câblé `app/embeddings_client.py`).
- frontend : Nuxt 4, Pinia, `<VizSourcePin>` (F40).
**Storage**: PostgreSQL 16 + pgvector ; nouvelle table `unsourced_flag`, ALTER de `agent_run`, `chat_message`, `source` (index ivfflat / hnsw cosine si absent).
**Testing**: pytest (markers `unit` / `integration` / `perf`) + pytest-cov ≥ 80% ; vitest pour helpers frontend ; Playwright pour E2E UX (chips + popover) ; golden set jsonl 50 cas (FR-015, NFR-003).
**Target Platform**: Linux server (UE / Afrique de l'Ouest uniquement, jamais US — RGPD + UEMOA 20/2010 + loi ivoirienne 2013-450).
**Project Type**: Web service (backend FastAPI) + Web app (Nuxt 4) + Browser extension MV3 (sidepanel F52).
**Performance Goals**:
- Détecteur : < 50 ms p95 sur 2 000 caractères (NFR-001).
- `search_source` : < 500 ms p95 (Voyage embed + pgvector cosine sur 10 k sources fixture) (NFR-002).
- Validateur (post-LLM) : < 100 ms p95 ajouté au cycle agent (NFR-008).
**Constraints**:
- Aucun déploiement US (RGPD + UEMOA + loi ivoirienne).
- Pas de `LLM_AGENT_SOURCING_MODE=off` en production (fail-fast au boot — FR-007).
- Coverage ≥ 80 % (`backend/pyproject.toml fail_under=80`).
- Détecteur synchrone (NFR-005), aucune dépendance LLM.
- Précision golden set : recall ≥ 0.90, precision ≥ 0.85 ; CI échoue sinon (NFR-003 / FR-015).
**Scale/Scope**:
- Sources : ~ 1 k initiales (F03/F07 catalogue), cible 10 k MVP, 100 k post-MVP.
- Conversations : ~10 messages assistant /jour /PME × 1 000 PME = 10 k messages /jour ⇒ 10 k détections /jour soutenues.
- `unsourced_flag` : ~100 inserts /jour MVP ; backlog admin paginé.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | F56 EST l'enforcement de P1. Toute donnée factuelle introduite (chiffres dans réponses LLM) DOIT pointer vers une `Source` `verified` via `cite_source`. | ✅ |
| P2 | Multi-tenant RLS | Nouvelle table `unsourced_flag` : `account_id NOT NULL` + RLS policy `USING (account_id = current_setting(...)::uuid)`. Cross-tenant → 404 (validateur FastAPI). | ✅ |
| P3 | Audit log append-only | `unsourced_flag` UPDATE/DELETE révoqués sur `app_user` ; `resolved_at`/`resolved_by` uniquement via rôle admin. Toute mutation par `flag_unsourced` est tracée via `tool_call_log` (F55). | ✅ |
| P4 | Versioning + snapshot candidatures | F56 ne modifie aucun référentiel ni candidature. N/A | ✅ |
| P5 | Money typé | F56 ne manipule aucune valeur monétaire (le détecteur lit du texte ; les chiffres détectés ne sont pas typés `Money`). N/A | ✅ |
| P6 | Pivot Indicateur unique | Aucune duplication d'indicateur. F56 ne crée pas de table E/S/G. N/A | ✅ |
| P7 | Plateforme fermée aux intermédiaires | Endpoint `/admin/agent/metrics/sourcing` gardé admin (rôle `Admin`). Aucun rôle Bank/Fund/Intermédiaire. Pas de webhook externe. | ✅ |
| P8 | Édition manuelle + sync LLM | `chat_message.sources` est calculé à partir des `tool_calls` LLM. La résolution d'un `unsourced_flag` (admin) écrit `resolved_at/by`. Pas de propagation EventBus en MVP F56 (les sources de message sont read-only post-`message_done`). | ✅ |
| P9 | Tool-use LLM fiable | 3 nouveaux tools (`cite_source`, `search_source`, `flag_unsourced`) avec schéma Pydantic v2 `extra='forbid'` ; docstring "use when / don't use when" ; eval gating planifié (`tests/llm_eval/sourcing_eval.py`). Hard cap matériel `HARD_TOOL_CALLS_CAP=10` reste actif (les 3 tools sourcing sont **forcés exposés** au-delà du cap métier mais le LLM n'appelle jamais 13 tools dans un tour ; le `tool_calls_count_in_turn` continue de plafonner à 10 calls par tour). | ✅ |
| P10 | UX bottom sheet | F56 ne crée aucun composant interactif. Les chips Source (US7) sont du **rendu inline non interactif** (superscript cliquable → popover read-only) ; conforme P10 (le popover ne demande pas d'input utilisateur). Le bouton "Répondre librement" demeure dans la chat shell F41. | ✅ |

**All gates pass — no Complexity Tracking entries needed.**

### Contraintes techniques (rappel)

- Stack imposée respectée : FastAPI + Python 3.12 + Nuxt 4 + Pydantic v2 + Voyage `voyage-3.5` + pgvector + OpenRouter `minimax-m2.7`.
- Dev local : backend `.venv`, Postgres seul service docker, `make backend` / `make frontend`.
- Hébergement : UE / Afrique de l'Ouest uniquement.
- Conformité : `unsourced_flag.account_id` ⇒ RGPD/UEMOA OK ; aucune PII supplémentaire (les claims sont du texte généré, pas des données nominatives).
- Langue : claims FR uniquement en MVP (whitelist FR ; détecteur regex FR). EN sera ajouté post-MVP via overlay regex.

## Project Structure

### Documentation (this feature)

```text
specs/056-agent-sourcing-enforcement/
├── plan.md                       # This file
├── research.md                   # Phase 0 output
├── data-model.md                 # Phase 1 output
├── quickstart.md                 # Phase 1 output
├── contracts/
│   ├── tool-registry.md          # Schémas Pydantic des 3 nouveaux tools
│   ├── sourcing-validator.md     # API du validator
│   ├── sse-events.md             # Events SSE émis (message_done.sources, unsourced_claim)
│   └── admin-metrics.md          # OpenAPI partial du endpoint admin
├── checklists/
│   └── requirements.md           # Quality checklist
└── tasks.md                      # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── agent/
│   │   ├── sourcing/                        # NEW (F56)
│   │   │   ├── __init__.py
│   │   │   ├── detector.py                  # FR-001 detect_claims()
│   │   │   ├── validator.py                 # FR-002 validate_response()
│   │   │   ├── whitelist.py                 # FR-014 patterns
│   │   │   ├── normalizer.py                # claim normalization for dedup (Q1)
│   │   │   └── models.py                    # Claim, ClaimKind, SourcingValidationResult, SourceRef
│   │   ├── handlers/                        # F55 existing
│   │   │   ├── cite_source.py               # NEW — verifies source.verified
│   │   │   ├── search_source.py             # NEW — Voyage + pgvector cosine
│   │   │   └── flag_unsourced.py            # NEW — INSERT unsourced_flag + SSE
│   │   ├── nodes/
│   │   │   ├── select_tools.py              # MODIFY — force 3 sourcing tools
│   │   │   ├── compose_response.py          # MODIFY — post-LLM validate + retry
│   │   │   └── (recall_memory.py — DO NOT TOUCH, F57 zone)
│   │   ├── state.py                         # MODIFY — add sourcing_retry_count + sourcing_decision
│   │   ├── dispatcher.py                    # MINIMAL MODIFY — register new READ tools in _REINVOKE_HANDLERS
│   │   └── sse_bridge.py                    # MINIMAL MODIFY — emit unsourced_claim event
│   ├── orchestrator/
│   │   └── tool_registry.py                 # MODIFY — register cite_source, search_source, flag_unsourced
│   ├── admin/
│   │   └── agent_metrics.py                 # NEW — GET /admin/agent/metrics/sourcing
│   ├── models/
│   │   └── unsourced_flag.py                # NEW — SQLAlchemy model
│   ├── main.py                              # MINIMAL MODIFY — mount admin metrics router
│   └── config.py                            # MODIFY — add LLM_AGENT_SOURCING_MODE setting
├── alembic/
│   └── versions/
│       └── 0035_f56_unsourced_flag_and_sourcing_columns.py   # NEW
└── tests/
    ├── unit/
    │   ├── test_sourcing_detector.py        # NEW
    │   ├── test_sourcing_validator.py       # NEW
    │   └── test_sourcing_whitelist.py       # NEW
    ├── integration/
    │   ├── test_cite_source_handler.py      # NEW
    │   ├── test_search_source_handler.py    # NEW (Voyage mocké + pgvector réel)
    │   ├── test_flag_unsourced_handler.py   # NEW (RLS + dedup ON CONFLICT)
    │   ├── test_select_tools_force_sourcing.py  # NEW
    │   ├── test_compose_response_retry.py   # NEW (3 modes + retry)
    │   ├── test_admin_metrics_sourcing.py   # NEW
    │   └── test_sourcing_e2e_strict.py      # NEW — agent run réel mocké LLM, mode strict
    ├── perf/
    │   └── test_sourcing_perf.py            # NEW — NFR-001/002/008
    ├── golden/
    │   └── sourcing.jsonl                   # NEW — 50 cas (FR-015)
    └── llm_eval/
        └── sourcing_eval.py                 # NEW — eval gating golden set

frontend/                                    # F41 + F52 only (consumers)
├── app/
│   ├── components/chat/
│   │   └── MessageSources.vue               # NEW — superscripts + popover (US7) ; uses <VizSourcePin>
│   └── stores/
│       └── chat.ts                          # MODIFY — store payload.sources from SSE
└── tests/
    └── e2e/
        └── chat-sources-rendering.spec.ts   # NEW — Playwright (US7)

extension/sidepanel/                         # F52 sidepanel consumes same SSE
├── src/views/chat/
│   └── (consume payload.sources, render minimal chip — same store layer)
└── __tests__/
    └── chat-sources.spec.ts                 # NEW — vitest unit
```

**Structure Decision**: Domain-per-feature. F56 lives in 4 zones :

1. `backend/app/agent/sourcing/` (new package, MIT — pure logic, no DB).
2. `backend/app/agent/handlers/{cite,search,flag}*.py` (3 new handlers, integrated with F55 dispatcher).
3. `backend/alembic/versions/0035_*.py` (single migration, idempotent + reversible).
4. `frontend/app/components/chat/MessageSources.vue` + `extension/sidepanel/...` (consumers of SSE `payload.sources`).

The agent reuses F53 LangGraph state/checkpointer, F54 prompts (fed by `app/agent/prompts/identity.py` + `invariants.py`), and F55 dispatcher categories (`READ` / `MUTATION` / `REINVOKE_LLM`). No new orchestration layer.

## Complexity Tracking

*All Constitution gates pass.* No entries.

## Phase 0 — Research outputs

See [research.md](./research.md). All NEEDS CLARIFICATION resolved during the clarify phase.

Key decisions :

- **Detection algorithm**: regex + keyword + whitelist (no LLM-judge in MVP). Deterministic and < 50 ms.
- **Cross-reference granularity**: paragraph-level (a `cite_source` invocation in the same paragraph "covers" all claims of that paragraph). Sentence-level deferred post-MVP.
- **Retry strategy**: max 1 sourcing retry per turn, with explicit ToolMessage system listing the unsourced spans. If retry fails → fallback truncation or substitution.
- **Voyage AI down**: fallback `ILIKE %query%` on `title` + `section` ; response includes `degraded=true`.
- **Dedup unsourced_flag**: UNIQUE partial index `(account_id, thread_id, lower(claim)) WHERE resolved_at IS NULL` ; INSERT uses `ON CONFLICT DO NOTHING`.
- **Permissive auto-flag**: per-message rollup, not per-claim ; `claim` = first detected, `reason='auto_detected:N'`.
- **pgvector pre-warm**: post-MVP. MVP relies on cold-cache acceptable latency.
- **Strict mode in prod**: enforced at boot (`config.py` raises on `LLM_AGENT_SOURCING_MODE=off` when `ENVIRONMENT=production`).

## Phase 1 — Design & contracts

See:

- [data-model.md](./data-model.md) — schemas, indexes, RLS policies.
- [contracts/tool-registry.md](./contracts/tool-registry.md) — Pydantic schemas for the 3 new tools.
- [contracts/sourcing-validator.md](./contracts/sourcing-validator.md) — internal API of the validator.
- [contracts/sse-events.md](./contracts/sse-events.md) — `message_done.sources`, `unsourced_claim`.
- [contracts/admin-metrics.md](./contracts/admin-metrics.md) — admin metrics endpoint.
- [quickstart.md](./quickstart.md) — runtime walkthrough (3 modes, ASCII timeline).

Constitution re-check after design: **all gates still pass** (no new violations introduced by the design).

## Phase 2 — Tasks (deferred to /speckit-tasks)

Tasks will be generated by `/speckit-tasks` from this plan + spec. Expected ~ 38 tasks (split unit, integration, perf, eval, frontend, e2e), grouped by user story (US1-US10), with TDD-first ordering.
