# Implementation Plan: F14 — LangGraph Routing & Pydantic Validation Pipeline

**Branch**: `014-langgraph-routing-validation` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/014-langgraph-routing-validation/spec.md`

## Summary

F14 livre le **moteur d'orchestration** du tool-use : pipeline `classifier → tool selector → system prompt builder → LLM principal → Pydantic validator → retry (max 2) → fallback texte`. Aucun tool métier n'est livré ici — F14 fournit la *convention de déclaration* (`@tool` + registre), 5 tools fictifs comme harnais de test, une nouvelle table `tool_call_log` (append-only, RLS par `account_id`), et le branchement derrière l'endpoint chat existant (F13). Streaming SSE étendu avec les events `thinking / tool_call_started / tool_call_completed`. Le routage multi-modèle, le cache sémantique et les Skills (F19) sont hors scope.

## Technical Context

**Language/Version** : Python 3.11+ (backend, venv local `backend/.venv`).
**Primary Dependencies** : FastAPI, SQLAlchemy 2 (sync `Session` aligné F13), Alembic, Pydantic v2 (avec `ConfigDict(extra='forbid')`), `openai` SDK (configuré sur OpenRouter), `httpx`, `cachetools` (LRU TTL en mémoire).
**Storage** : PostgreSQL 16 + pgvector (déjà provisionné). Nouvelle table `tool_call_log`. Pas de Redis (cache d'intention en mémoire processus, conformément à clarification Q1).
**Testing** : pytest + pytest-asyncio + pytest-cov ; cible ≥ 80 % sur les modules nouveaux.
**Target Platform** : conteneur Linux (déploiement Europe/Afrique de l'Ouest), Postgres dockerisé en dev local.
**Project Type** : Web application (backend FastAPI + frontend Nuxt 4 ; F14 = backend uniquement).
**Performance Goals** : surcoût pipeline < 1 s p95 (hors temps LLM principal) ; system prompt ≤ 4 000 tokens.
**Constraints** : multi-tenant RLS stricte par `account_id` ; audit append-only ; tools ≤ 10 par tour (limite hard) ; max 2 retries ; cache LRU TTL 10 min (par `thread_id`) ; sérialisation des pipelines par `thread_id` (verrou logiciel).
**Scale/Scope** : ~10 PME pilotes en MVP, ~5 messages/PME/jour, soit < 100 appels LLM/jour côté pipeline. Scaling cible 1 000 PME visé en post-MVP.

## Constitution Check

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | F14 livre le moteur ; aucune *donnée* factuelle nouvelle. Les tools fictifs servent d'harnais et n'introduisent pas de fait. Le moteur, lui, *garantit* que les futurs tools auront un schéma strict (Module 10). | OK |
| P2 | Multi-tenant RLS | `tool_call_log` porte `account_id NOT NULL` + politique RLS `USING (account_id = current_setting('app.account_id')::uuid)`. Index dédié `(account_id, created_at DESC)`. | OK |
| P3 | Audit log append-only | `tool_call_log` est insert-only par construction (pas d'`UPDATE`/`DELETE` côté code). Les audit log F04 ne sont pas affectés. | OK |
| P4 | Versioning + snapshot | N/A — F14 n'introduit pas de référentiel. | OK |
| P5 | Money typé | N/A — F14 ne manipule pas de montants. Les tools fictifs évitent volontairement les champs `Money`. | OK |
| P6 | Pivot Indicateur unique | N/A — F14 n'introduit pas de donnée ESG. | OK |
| P7 | Plateforme fermée aux intermédiaires | F14 reste interne au backend ; pas d'exposition externe nouvelle. | OK |
| P8 | Édition manuelle + sync LLM | Le validateur Pydantic + l'erreur structurée sont précisément le contrat qui rend la mutation par LLM compatible avec l'édition manuelle (les schémas sont les mêmes que ceux des endpoints F11/F12). | OK |
| P9 | Tool-use LLM fiable | **Cœur de la feature** : convention `@tool` (nom verbal, use_when, dont_use_when, examples), schéma Pydantic strict (`extra='forbid'`), ≤ 10 tools concurrents par tour (limite hard testée), retry max 2, fallback texte, log append-only pour eval future (F35). | OK |
| P10 | UX bottom sheet | N/A backend ; le contrat SSE étendu (events `tool_call_started/completed`) reste compatible avec l'UI bottom sheet F13. | OK |

**Verdict** : aucun gate violé. Phase 0 peut démarrer.

### Contraintes techniques (rappel)

- Stack imposée respectée : FastAPI + Postgres + OpenRouter (via SDK `openai` réutilisé).
- Pas de Redis (cache LRU mémoire processus suffit en MVP, FR-013).
- Pas de routage multi-modèle (un seul `LLM_MODEL` configuré ; le classifier réutilise le même modèle avec un prompt court spécialisé, FR-014).
- Hébergement Europe/Afrique de l'Ouest, RGPD/2013-450/UEMOA déjà couverts par F02/F05.
- Langue FR par défaut (les anti-exemples et exemples du system prompt sont en FR).

## Project Structure

### Documentation (this feature)

```text
specs/014-langgraph-routing-validation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── sse-events-f14.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── orchestrator/                       # NOUVEAU module F14
│   │   ├── __init__.py
│   │   ├── tool_registry.py                # @tool decorator + TOOL_REGISTRY
│   │   ├── intent_classifier.py            # règles + fallback LLM + cache LRU TTL
│   │   ├── tool_selector.py                # règles déclaratives, limite hard 10
│   │   ├── system_prompt_builder.py        # invariants + arbre décision + tools
│   │   ├── payload_validator.py            # Pydantic strict + erreur structurée
│   │   ├── retry_policy.py                 # max 2 retries + fallback texte
│   │   ├── pipeline.py                     # respond() — orchestration end-to-end
│   │   ├── thread_lock.py                  # verrou par thread_id (asyncio.Lock)
│   │   └── fixtures_tools.py               # 5 tools fictifs (harnais de test)
│   ├── chat/
│   │   ├── api.py                          # MODIFIÉ : branche pipeline derrière /chat
│   │   └── llm_stream.py                   # MODIFIÉ : nouveaux events SSE
│   └── models/
│       └── tool_call_log.py                # NOUVEAU SQLAlchemy ORM
├── alembic/versions/
│   └── 20260429_xxxx_add_tool_call_log.py  # NOUVEAU (table + RLS + index)
└── tests/
    ├── orchestrator/
    │   ├── test_tool_registry.py
    │   ├── test_intent_classifier.py
    │   ├── test_tool_selector.py
    │   ├── test_system_prompt_builder.py
    │   ├── test_payload_validator.py
    │   ├── test_retry_policy.py
    │   ├── test_pipeline_e2e.py            # 10 cas test SC-001
    │   ├── test_thread_lock.py
    │   └── conftest.py
    └── chat/
        └── test_chat_api_pipeline.py
```

**Structure Decision** : conserve la convention F13 (modules par feature dans `backend/app/`). Module `orchestrator/` autonome, importable par `chat/api.py` mais sans dépendance inverse. Pas de package `langgraph` runtime — l'orchestration est implémentée en Python pur (≈500 LOC), suffisant pour MVP, plus simple à tester et à étendre.

## Phase 0 — Research

### R-1 : LangGraph vs orchestrateur Python maison ?

**Decision** : orchestrateur Python maison (≈500 LOC), pas de dépendance LangGraph en MVP.

**Rationale** : (1) le pipeline F14 est **linéaire** (classifier → selector → builder → LLM → validator → retry) sans branchements complexes ni état partagé multi-agents ; LangGraph apporte un graph runtime + state checkpointer dont nous n'avons aucun besoin en MVP. (2) Pas de dépendance externe supplémentaire à maintenir/auditer. (3) Tests unitaires triviaux sur des fonctions pures. (4) Le nom "langgraph" du module/feature est un terme de domaine, pas un engagement technique.

**Alternatives considérées** : `langgraph` (rejetée — overkill MVP), `temporal` (rejetée — orchestration distribuée hors scope), `prefect` (rejetée — workflow batch).

### R-2 : Cache d'intention par fil — implémentation

**Decision** : `cachetools.TTLCache` (capacité 1024, TTL 600 s glissant) en mémoire processus, clé = `(account_id, thread_id)`.

**Rationale** : FR-013 — pas de Redis MVP. `cachetools` est déjà testé, thread-safe avec lock, et 0 dépendance lourde. Capacité 1024 suffisante pour ~10 PME × ~100 fils actifs simultanés. Clé incluant `account_id` empêche toute fuite cross-tenant même en cas de collision UUID théorique.

**Alternatives** : `functools.lru_cache` (rejetée — pas de TTL), Redis (rejetée — out of MVP scope), dict + cleanup périodique (rejetée — bug-prone).

### R-3 : Retry sur erreur de validation — limite et budget

**Decision** : `max_retries = 2` (donc 3 appels LLM au total), avec **prompt minimal** au retry (uniquement nom du tool ciblé + schéma + erreur structurée + dernier message user, **pas** l'historique). Tokens retry comptés séparément (FR-011).

**Rationale** : économie de tokens, traçabilité du coût plateforme distinct du quota PME, limite stricte testable.

### R-4 : Sérialisation par thread_id

**Decision** : registre `dict[(account_id, thread_id), asyncio.Lock]` global, garbage-collecté quand le compteur de waiters tombe à 0. Verrou acquis à l'entrée de `respond()`, libéré dans un `finally`.

**Rationale** : FR-016 ; évite les race-conditions sur le cache d'intention et la cohérence du contexte. Implémentation triviale (~30 LOC), testable avec `asyncio.gather`.

### R-5 : Format SSE des nouveaux events

**Decision** : 3 nouveaux events ajoutés à l'enveloppe F13 :

```
event: thinking
data: {"step": "classifying" | "selecting_tools" | "calling_llm" | "validating" | "retrying"}

event: tool_call_started
data: {"tool_name": "...", "call_id": "uuid"}

event: tool_call_completed
data: {"tool_name": "...", "call_id": "uuid", "status": "ok" | "validation_error" | "handler_error" | "timeout", "result_preview": {...}}
```

`text_delta` et `message_done` restent inchangés (F13).

### R-6 : Détection d'intention — règles MVP

**Decision** : 6 mappings regex/keyword pour {profilage, mutation, analyse, navigation, question_fermee, aide} ; tout le reste → `autre` ou bascule vers le LLM léger si confiance < seuil. Liste de patterns commitée dans `intent_classifier.py`.

**Rationale** : déterministe, testable, facile à évoluer ; le LLM est un fallback rare, pas la voie principale.

## Phase 1 — Design & Contracts

### Data Model

Voir [data-model.md](./data-model.md) pour la définition complète.

Résumé : une seule entité nouvelle, `ToolCallLog` (table `tool_call_log`), append-only, RLS par `account_id`. Pas d'autre table métier.

### Contracts

Voir [contracts/sse-events-f14.md](./contracts/sse-events-f14.md) pour le contrat SSE étendu.

Pas de nouvel endpoint REST : F14 se branche derrière `/chat/messages` (F13) sans changer la signature. Un endpoint admin lecture-seule `GET /admin/tool-call-logs?thread_id=...&status=...` est livré pour la validation manuelle (FR-008 + SC-005), restreint aux rôles admin.

### Quickstart

Voir [quickstart.md](./quickstart.md) — comment déclarer un tool, comment exécuter les tests E2E, comment activer le mode stub LLM.

### Agent context update

Met à jour `CLAUDE.md` (section SPECKIT) pour pointer sur ce plan.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| (aucune) | — | — |

Tous les principes constitutionnels sont satisfaits sans dérogation.

## Phase 2 — Tasks (preview only)

Le découpage détaillé est généré par `/speckit-tasks`. Préfiguration :

- T1 — Migration Alembic `tool_call_log` (table + RLS + index).
- T2 — Modèle ORM `ToolCallLog`.
- T3 — `tool_registry.py` + decorator `@tool` + 5 tools fictifs (TDD).
- T4 — `intent_classifier.py` (règles + cache + LLM fallback) (TDD).
- T5 — `tool_selector.py` (règles, limite 10, defaults) (TDD).
- T6 — `system_prompt_builder.py` (briques + plafond tokens + alarme) (TDD).
- T7 — `payload_validator.py` (Pydantic strict + erreur structurée) (TDD).
- T8 — `retry_policy.py` (max 2 + fallback) (TDD).
- T9 — `thread_lock.py` (sérialisation par thread_id) (TDD).
- T10 — `pipeline.py` `respond()` E2E + SSE events (TDD).
- T11 — Branchement dans `chat/api.py` (sans casser F13).
- T12 — Endpoint admin lecture `/admin/tool-call-logs`.
- T13 — Tests d'intégration API + SSE F14.
- T14 — Couverture ≥ 80 % vérifiée + lint vert.

## Risks & Mitigations

- **Régression F13** : tests F13 existants doivent continuer à passer (LLM stub). Mitigation : pipeline désactivable via `F14_PIPELINE_ENABLED` (défaut on en dev/test, mais le mode stub bypasse le pipeline si `LLM_STUB=1`).
- **Coût retry explosif** : limite hard 2 + prompt minimal. Mitigation : test unitaire qui mesure le nb de tokens du retry et asserte qu'il est < 25 % du prompt initial.
- **Drift schéma/description** : la déclaration `@tool` est unique. Mitigation : un test introspecte le registre et vérifie que chaque tool expose les 5 champs requis.
- **Verrou par thread bloquant** : timeout court (5 s) sur l'acquisition pour éviter les hangs.
