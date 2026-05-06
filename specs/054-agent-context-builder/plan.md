# Implementation Plan: Agent Context Builder & System Prompt dynamique (F54)

**Branch**: `054-agent-context-builder` | **Date**: 2026-05-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/054-agent-context-builder/spec.md`

## Summary

F54 enrichit le squelette LangGraph de F53 (déjà mergé) en construisant à chaque tour un **system prompt dynamique** combinant identité figée ESG Mefali, invariants Module 0, skills actives, outils disponibles, contexte porteur (entreprise/projets/candidatures/scores/plan d'action), contexte de page courante, réponse structurée bottom sheet et métadonnées tour. Approche technique : **f-strings + dataclasses immutables** (pas Jinja2), **cache LRU process-local hybride** (EventBus push F41 + TTL 60s fallback), **soft caps loader** (10 projets / 10 candidatures / 30 indicateurs), **stratégie de troncature ordonnée** garantissant ≤ 4 000 tokens dans 99 % des cas, et **endpoint admin** `GET /admin/agent-runs/{id}/prompt` pour rejouabilité (hash en mode normal, prompt en clair seulement si error). Couverture cible ≥ 90 %.

## Technical Context

**Language/Version**: Python 3.12 (backend) ; pas de modification frontend pour F54
**Primary Dependencies**:
- Backend déjà installées : FastAPI, SQLAlchemy 2 (async), Pydantic v2, langgraph, langchain-core, structlog, slowapi, pytest, pytest-asyncio, pytest-cov.
- **Ajout F54** : `tiktoken` (count tokens, encoding `cl100k_base`) — déjà disponible via OpenAI/LangChain, vérifier `pyproject.toml`.
**Storage**: PostgreSQL 16 + pgvector (RLS). Pas de table nouvelle. ALTER `agent_run` (ajout `system_prompt_hash CHAR(64)`, `prompt_version VARCHAR(16)`).
**Testing**: pytest + pytest-asyncio + pytest-cov ; markers `unit | integration | e2e | perf`. Snapshots via `syrupy` (déjà dans pyproject) OU comparaison string brute (orchestrateur autorise simple file-fixture).
**Target Platform**: Linux server (Ubuntu 22.04, Python 3.12) hébergement Europe/Afrique de l'Ouest.
**Project Type**: Web service — backend Python + frontend Nuxt (frontend non touché par F54, sauf E2E Playwright pour SC-003 multi-tenant).
**Performance Goals**:
- Build context (loader + builder) < 250 ms p95 cold cache.
- < 50 ms p95 hot cache.
- Prompt ≤ 4 000 tokens dans 99 % des cas. Jamais > 6 000 tokens.
**Constraints**:
- Service pur — aucune dépendance directe vers `chat/api.py` ou `agent/runner.py` (NFR-004).
- RLS strict P2 — clé cache inclut `account_id`.
- Anti-injection : escape `{` → `{{` + cap `MAX_FIELD_LEN = 500` chars sur tous les fields PME (FR-013).
- Identité ESG Mefali immuable, jamais nommer minimax/GPT/Claude (SC-009).
**Scale/Scope**:
- ~5 modules nouveaux (`prompts/invariants.py`, `context_loader.py`, `prompt_builder.py`, `cache.py`, `tokens.py`) + 1 endpoint admin + 8 nœuds modifiés (build_context, recall_memory).
- 30 tests unitaires + 6 tests integration + 2 tests E2E Playwright + 1 test eval (golden set 5 variantes identité + 5 variantes jailbreak).
- Bibliothèque interne consommée par F55 (dispatch), F56 (sourcing), F57 (memory), F58 (guardrails).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | F54 ne crée aucune donnée factuelle directement. Il **transmet** le contexte (entreprise, projets, indicateurs avec `source_id`). Le tool-use validator F56 reste responsable de bloquer un `compose_response` sans `cite_source`. F54 expose les `source_id` dans le bloc indicateurs pour permettre au LLM de citer. | ✅ |
| P2 | Multi-tenant RLS | Pas de table nouvelle. `account_id` est partout dans la clé de cache + dans toutes les requêtes du `context_loader` (filtre `WHERE account_id = current_setting('app.current_account_id')::uuid`). Test E2E NFR-003 valide isolation A vs B. Cross-tenant → 404 via RLS. | ✅ |
| P3 | Audit log append-only | F54 lit uniquement les données ; pas de mutation. Aucun audit log à émettre. L'endpoint admin GET (FR-014) est lecture seule. | ✅ |
| P4 | Versioning + snapshot candidatures | Le contexte de page candidature charge le `snapshot_json` immutable (pas la version live des référentiels). `prompt_version` (FR-015) trace la version du template d'invariants utilisée — versioning du prompt lui-même. | ✅ |
| P5 | Money typé | Tous les champs montants des modèles `BusinessContext` et `EnrichedPageContext` typés `Money = {amount: Decimal, currency: ISO 4217}`. Conversion FCFA-EUR via peg fixe 655.957 (sourcé) ; USD via `fx_rate` snapshot quotidien. Affichage prompt en devise native + équivalent XOF entre parenthèses si multi-devise (NFR-006). | ✅ |
| P6 | Pivot Indicateur unique | Le bloc indicateurs charge des `Indicateur` (table pivot) avec leur `code`, `valeur`, `unite`, `source_id`, `date`. La présentation par axe E/S/G dans le prompt est une **vue** générée à la volée pour le LLM, pas un stockage dupliqué. | ✅ |
| P7 | Plateforme fermée aux intermédiaires | F54 distingue uniquement `user.role == 'admin'` vs PME (FR-018). Aucun rôle Intermédiaire/Bank/Fund. Pas d'attestation générée par F54 (lecture pure). | ✅ |
| P8 | Édition manuelle + sync LLM | Le cache `BusinessContext` est invalidé en push via EventBus in-process (F41) sur tout événement de mutation (`company_profile_updated`, `projet_updated`, etc.) **+ TTL 60s fallback**. SC-004 valide qu'une mutation manuelle est reflétée dans le tour suivant. | ✅ |
| P9 | Tool-use LLM fiable | F54 ne crée pas de tools. Il alimente la section "ARBRE DE DÉCISION TOOLS" du prompt avec les `use_when` / `dont_use_when` des tools déjà enregistrés (FR-012). Le selector F14/F55 garantit ≤ 10 tools concurrents. | ✅ |
| P10 | UX bottom sheet | F54 est purement backend ; le frontend reste tel quel. Le `sheet_result` (FR-017) suit la convention F39 (bottom sheet → payload structuré). | ✅ |

**Verdict** : 10/10 ✅ — aucune violation. Pas d'entrée Complexity Tracking nécessaire.

### Contraintes techniques (rappel)

- Stack imposée : FastAPI + Python 3.12 + Pydantic v2 + SQLAlchemy 2 async + PostgreSQL/pgvector + tiktoken (ajout). Pas de Redis pour MVP.
- Dev local : backend en `.venv` ; backend démarre via `make backend` (port 8010) ; tests via `pytest` depuis `backend/.venv`.
- Hébergement production : Europe/Afrique de l'Ouest uniquement.
- Conformité : RGPD (snapshot prompt en clair UNIQUEMENT pour status='error', sinon hash → minimisation des données).
- Langue : système prompt construit en français par défaut.

## Project Structure

### Documentation (this feature)

```text
specs/054-agent-context-builder/
├── plan.md              # This file
├── spec.md              # Feature spec (with Clarifications)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (admin endpoint OpenAPI fragment + python protocol stubs)
│   ├── admin-prompt-endpoint.yaml
│   └── python-interfaces.md
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── agent/
│   │   ├── prompts/                    # NEW package
│   │   │   ├── __init__.py
│   │   │   ├── invariants.py           # FR-001 — INVARIANTS_TEMPLATE + PROMPT_VERSION
│   │   │   └── identity.py             # NEW — bloc d'identité ESG Mefali figé (séparé pour test)
│   │   ├── context/                    # NEW package (zone propre F54)
│   │   │   ├── __init__.py
│   │   │   ├── models.py               # FR-003 — BusinessContext, EnrichedPageContext, PromptParts, TruncationReport
│   │   │   ├── loader.py               # FR-002 — load_business_context, load_page_context
│   │   │   ├── cache.py                # FR-007 — LRU + EventBus subscriber + TTL fallback
│   │   │   ├── tokens.py               # FR-005 — count_tokens (tiktoken + heuristic fallback)
│   │   │   ├── truncation.py           # FR-006 — truncate_prompt + strategy
│   │   │   └── escape.py               # FR-013 — escape_template_chars + truncate_field
│   │   ├── prompt_builder.py           # FR-004 — build_system_prompt (orchestrates blocks)
│   │   ├── nodes/
│   │   │   ├── build_context.py        # MODIFIED (cible F54) — appelle context_loader + prompt_builder
│   │   │   └── recall_memory.py        # MODIFIED (cible F54) — injecte 15 derniers messages
│   │   ├── admin_router.py             # NEW — endpoint GET /admin/agent-runs/{id}/prompt (FR-014)
│   │   └── repository.py               # MODIFIED — ajoute persist_prompt_hash (FR-015)
│   ├── alembic/versions/
│   │   └── 0XYY_alter_agent_run_prompt_hash.py    # NEW migration ALTER (system_prompt_hash, prompt_version)
│   ├── eventbus/                       # potentially used (F41)
│   │   └── (read-only consumption)
│   └── main.py                         # MINIMAL TOUCH — register admin_router (low conflict risk avec F55)
├── tests/
│   ├── unit/agent/context/
│   │   ├── test_invariants_snapshot.py        # SC-008 (snapshot)
│   │   ├── test_business_context_loader.py    # 3 cas vide + cas standard
│   │   ├── test_page_context_loader.py        # 4 cas page (Projet/Candidature/Indicateur/Scoring)
│   │   ├── test_truncation_strategy.py        # 6 cas troncature
│   │   ├── test_tokens.py                     # tiktoken + fallback
│   │   ├── test_escape.py                     # FR-013 cas limites
│   │   ├── test_cache.py                      # LRU + EventBus invalidation + TTL
│   │   └── test_prompt_builder.py             # composition full prompt
│   ├── integration/agent/
│   │   ├── test_build_context_node.py         # nœud LangGraph build_context end-to-end
│   │   ├── test_recall_memory_node.py         # injection 15 messages
│   │   ├── test_admin_prompt_endpoint.py      # FR-014 — hash vs full
│   │   └── test_multi_tenant_isolation.py     # NFR-003 cross-tenant
│   ├── e2e/agent/
│   │   ├── test_identity_resilience.py        # SC-009 — 5 variantes "qui es-tu"
│   │   └── test_jailbreak_resilience.py       # SC-010 — 5 variantes jailbreak
│   └── perf/agent/
│       └── test_build_context_latency.py      # NFR-001 (cold/hot)
└── pyproject.toml                       # ADD tiktoken (>=0.7) si absent

frontend/
└── tests/e2e/                           # ZONE F55 SHARED — 1 test E2E lecture-seule mince
    └── agent-context-isolation.spec.ts  # SC-003 — multi-tenant via UI (lit le prompt via endpoint admin)
```

**Structure Decision**: F54 crée un sous-package `app/agent/context/` (zone propre) regroupant tous les nouveaux modules (loader, cache, tokens, truncation, escape, models). Le `prompt_builder.py` reste à la racine de `app/agent/` car invoqué par les nœuds. Les nœuds existants (`build_context.py`, `recall_memory.py`) sont **enrichis** sans changer leur signature publique (zone propre F54). `admin_router.py` est nouveau et enregistré dans `main.py` (touche minimale anticipée comme conflit mineur avec F55, à fusionner manuellement). Aucun fichier partagé F55 n'est touché.

## Phase 0: Outline & Research

Toutes les ambiguïtés ont été résolues lors de la phase /speckit-clarify (5/5 questions). Recherche complémentaire nécessaire :

1. **tiktoken disponibilité et encoding pour minimax** — vérifier que `cl100k_base` est l'encoding correct par défaut, mesurer la dérive sur un échantillon de 100 prompts réels.
2. **EventBus in-process F41** — confirmer le contrat de subscription (`event_type`, `payload`) et les events émis par `update_company_profile`, `projet_updated`, etc.
3. **Best practices LRU thread-safe asyncio** — `functools.lru_cache` ne fonctionne pas avec coroutines async ; alternatives : `async-lru`, `cachetools.LRUCache + asyncio.Lock`, ou implémentation manuelle.
4. **Pattern "service pur" pour éviter dépendance circulaire** — comment garantir via lint qu'`app/agent/context/*` ne touche pas `chat/api.py` / `agent/runner.py` ?

Voir [research.md](./research.md) pour les décisions et alternatives.

**Output**: research.md ✅

## Phase 1: Design & Contracts

**Prerequisites:** research.md complete

1. **Entities** → [data-model.md](./data-model.md) :
   - `BusinessContext`, `EnrichedPageContext`, `PromptParts`, `TruncationReport`, `Money` (réutilisé), extension `AgentRun`.
   - Toutes les entités sont des dataclasses immutables Pydantic v2 `extra='forbid'`.

2. **Contracts** → [contracts/](./contracts/) :
   - **Admin endpoint** : `GET /admin/agent-runs/{run_id}/prompt` — renvoie `{run_id, status, system_prompt_hash, prompt_version, prompt?}` (prompt en clair uniquement si `status='error'`).
   - **Python protocol stubs** : signatures publiques des modules (loader, builder, cache, truncation) pour permettre aux features F55–F58 de consommer.

3. **Quickstart** → [quickstart.md](./quickstart.md) : guide dev pour exécuter localement les tests, mesurer la latence, valider le snapshot d'invariants.

4. **Agent context update** : pas de modification du `CLAUDE.md` (le `<!-- SPECKIT START -->` n'est pas présent dans le projet et le CLAUDE.md actuel pointe déjà sur la feature active via `.specify/feature.json`).

**Output**: data-model.md ✅, contracts/* ✅, quickstart.md ✅

## Re-evaluation Constitution Check (post-design)

- P1 ✅ : `source_id` exposé dans `BusinessContext.indicateurs[]` via dataclass.
- P2 ✅ : clé cache `(account_id, schema_version)` ; tests `test_multi_tenant_isolation.py` + `test_identity_resilience.py` valident.
- P3 ✅ : pas de mutation, lecture seule.
- P4 ✅ : `prompt_version` versionne le template d'invariants ; le contexte candidature lit `snapshot_json` immutable.
- P5 ✅ : `Money` utilisé partout dans les dataclasses.
- P6 ✅ : `BusinessContext.indicateurs[]` est une liste d'`Indicateur` (pivot) ; vue par axe générée dans le builder.
- P7 ✅ : seules deux branches (admin / PME) dans le bloc identité du prompt.
- P8 ✅ : `Cache.invalidate(account_id)` exposé pour subscription EventBus.
- P9 ✅ : section "ARBRE DE DÉCISION TOOLS" générée à partir des champs `use_when`/`dont_use_when` du registry.
- P10 ✅ : `sheet_result` injection conforme à la convention F39.

**Verdict post-design** : 10/10 ✅ — aucun nouveau risque introduit.

## Complexity Tracking

> Pas de violation à justifier — section laissée vide.
