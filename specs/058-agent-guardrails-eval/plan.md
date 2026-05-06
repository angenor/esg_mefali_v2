# Implementation Plan: F58 — Agent Guardrails, Resilience & Eval Continue

**Branch**: `058-agent-guardrails-eval` | **Date**: 2026-05-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/058-agent-guardrails-eval/spec.md`

## Summary

F58 livre la couche transversale de garde-fous, résilience et eval continue qui rend
production-ready l'agent ESG Mefali assemblé par F53–F57. Cinq guardrails Python purs
(`anti_injection`, `pii_detector`, `lang_check`, `circuit_breaker`, `budget`) sont
ajoutés sous `backend/app/agent/guardrails/`. Un kill-switch admin par tool (table
`agent_tool_status`) permet la désactivation à chaud. Une migration alembic 0037
étend `account` (3 sous-quotas) et `agent_run` (6 champs guardrails). Les nodes
existantes `route.py`, `select_tools.py`, `compose_response.py` sont enrichies sans
réécriture. L'endpoint admin `agent_metrics.py` est consolidé avec 6 sections (runs,
tools, sourcing F56, sécurité, coût, mémoire F57). Deux scripts d'éval CI
(`eval_agent.py` 50 cas + `eval_jailbreak.py` 100 cas) tournent en mode hybride :
mock sur chaque PR + real LLM nocturne / on-demand. Couverture cible ≥ 85 % sur
`app/agent/guardrails/`.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript / Vue 3 (frontend admin metrics page optionnelle)
**Primary Dependencies**: FastAPI 0.115+, SQLAlchemy 2.x, Alembic, Pydantic v2 (`extra='forbid'`), `langdetect` (lib légère pour FR-005), `httpx` (Slack webhook async, FR-022), `pytest` + `pytest-cov` (test gating ≥ 85 %)
**Storage**: PostgreSQL 16 + pgvector (réutilise schéma F53–F57). Nouvelle table `agent_tool_status` ; extensions `account` (3 sous-quotas) + `agent_run` (6 champs guardrails). Circuit breaker et compteurs tokens : in-memory par worker (FR-010 clarifié).
**Testing**: pytest avec markers `unit | integration | perf` ; vitest côté frontend si page admin livrée. Golden set agent (50 cas) + jailbreak (100 cas) en JSONL, runner Python.
**Target Platform**: Linux server (UE / Afrique de l'Ouest). Single uvicorn worker en MVP (clarification Q2). Pas de Redis MVP.
**Project Type**: Web application (backend FastAPI + frontend Nuxt 4 admin léger).
**Performance Goals**: Latence guardrails < 30 ms p95 par tour (NFR-001). Endpoint admin `/admin/agent/metrics?period=7d` < 500 ms p95.
**Constraints**: Coûts éval CI maîtrisés via mode hybride mock+real (clarification Q5). Forward-only PII masking (Q4). In-memory circuit breaker single-worker (Q2).
**Scale/Scope**: ~50 K tokens/jour/compte (sous-quotas 30 K + 20 K), 1000 PME en MVP, ~10 K agent_run/jour total.

## Constitution Check

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Le golden set agent inclut des cas qui vérifient l'invocation de `cite_source` (US8 cas sourçage). Les nouveaux modules guardrails ne produisent aucune assertion ESG/financière. | ✅ |
| P2 | Multi-tenant RLS | La nouvelle table `agent_tool_status` est **globale** (pas de `account_id`) car elle pilote le sélecteur de tools côté plateforme — accès admin uniquement (404 pour non-admin). Les extensions `account.daily_*_quota` et `agent_run.*` héritent de la RLS de leur table. | ✅ |
| P3 | Audit log append-only | Toute mutation sur `agent_tool_status` (disable/enable) est journalisée dans `audit_log` avec `source_of_change = 'admin'`. Les flags guardrails sur `agent_run` sont écrits une seule fois (immuables). | ✅ |
| P4 | Versioning + snapshot candidatures | F58 n'introduit ni nouveau référentiel ni candidature. Aucun impact. | ✅ |
| P5 | Money typé | Aucune valeur monétaire introduite. Estimation `$/jour` du dashboard est une projection cosmétique (non persistée), calculée depuis `tokens_in/out`. | ✅ |
| P6 | Pivot Indicateur unique | Aucun nouvel `Indicateur`. Les compteurs tokens sont des métriques techniques (pas ESG). | ✅ |
| P7 | Plateforme fermée aux intermédiaires | Les endpoints admin sont accessibles au rôle `Admin` ESG Mefali uniquement (pas d'intermédiaire). | ✅ |
| P8 | Édition manuelle + sync LLM | F58 n'introduit pas de champ alimenté par le LLM dans le domaine métier. Les flags `agent_run.*` sont système (non éditables). | ✅ |
| P9 | Tool-use LLM fiable | F58 **renforce** P9 : (a) eval gating ≥ 50 cas réalisé (FR-018), (b) golden set jailbreak (FR-024), (c) loop detection (FR-016) + budget (FR-013) + circuit breaker (FR-010) protègent l'agent assemblé. Pas de nouveau tool ; les tools existants restent en Pydantic strict. | ✅ |
| P10 | UX bottom sheet | La page admin `/admin/agent/metrics` est un dashboard read-only (pas d'inputs interactifs LLM). Aucun composant ne s'affiche dans une bulle LLM. | ✅ |

### Contraintes techniques (rappel)

- Stack imposée respectée : FastAPI + Python 3.12 + .venv ; pas de docker backend en dev.
- Hébergement EU/Afrique de l'Ouest. Slack webhook : URL fournie via env, no-op si absent.
- RGPD : masquage PII forward-only (Q4) ; logs masqués dans `agent_run`/`agent_run_step`/`tool_call_log`.
- Langue : français par défaut. Forçage FR via `lang_check` + retry (FR-006).

## Project Structure

### Documentation (this feature)

```text
specs/058-agent-guardrails-eval/
├── plan.md              # This file
├── spec.md              # Feature specification (with 5 clarifications)
├── research.md          # Phase 0 — research decisions
├── data-model.md        # Phase 1 — entity & migration design
├── quickstart.md        # Phase 1 — dev setup + manual test recipes
├── contracts/
│   ├── admin-tools.md          # POST /admin/agent/tools/{name}/disable|enable, GET /admin/agent/tools
│   ├── admin-metrics.md        # GET /admin/agent/metrics?period=...
│   ├── guardrails-api.md       # detect(), mask_pii(), detect_language(), is_open(), check_budget()
│   ├── eval-runner.md          # scripts/eval_agent.py + eval_jailbreak.py CLI + JSON report schema
│   └── ops-alerting.md         # send_alert() interface + Slack webhook payload
├── checklists/
│   └── requirements.md  # Spec quality checklist (already created)
└── tasks.md             # Phase 2 — generated by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── agent/
│   │   ├── guardrails/                 # NEW — F58 zone propre
│   │   │   ├── __init__.py
│   │   │   ├── anti_injection.py       # FR-001, FR-002 — detect() + wrap_user_message()
│   │   │   ├── pii_detector.py         # FR-003, FR-004 — mask_pii() (immutable)
│   │   │   ├── lang_check.py           # FR-005, FR-006 — detect_language() + retry FR
│   │   │   ├── circuit_breaker.py      # FR-010, FR-011 — in-memory per-worker
│   │   │   ├── budget.py               # FR-012-015 — check_budget() (2 sous-flux)
│   │   │   ├── tool_status.py          # FR-007-009 — kill-switch repo + cache TTL 30s
│   │   │   └── loop_detector.py        # FR-016 — hash args + counter
│   │   ├── runner.py                   # MODIFIED — insertion guardrails dans la boucle
│   │   ├── nodes/
│   │   │   ├── route.py                # MODIFIED — anti_injection + lang_check
│   │   │   ├── select_tools.py         # MODIFIED — filter par tool_status + minimal mode
│   │   │   ├── call_llm.py             # MODIFIED — circuit_breaker.is_open() + budget cap
│   │   │   └── compose_response.py     # MODIFIED — lang retry + force on tool_calls > 10
│   │   └── (autres existants F53-F57)  # UNTOUCHED
│   ├── admin/
│   │   ├── agent_metrics.py            # MODIFIED — extension consolidée 6 sections
│   │   └── agent_tools.py              # NEW — endpoints kill-switch (FR-007)
│   ├── utils/
│   │   └── ops_alerting.py             # NEW — send_alert() + Slack webhook
│   ├── models/
│   │   ├── agent_tool_status.py        # NEW — SQLAlchemy model
│   │   └── (account.py, agent_run.py)  # MODIFIED — extension columns
│   └── main.py                         # MODIFIED — register agent_tools router
├── alembic/
│   └── versions/
│       └── 0037_f58_guardrails.py      # NEW — table + 9 columns
├── scripts/
│   ├── eval_agent.py                   # NEW — runner golden set 50 cas (mock + real)
│   ├── eval_jailbreak.py               # NEW — runner 100 prompts (mock + real)
│   └── check-bundle-size.mjs           # UNTOUCHED (F52)
├── tests/
│   ├── unit/
│   │   ├── agent/guardrails/
│   │   │   ├── test_anti_injection.py  # NEW — 10 cas (FR-026)
│   │   │   ├── test_pii_detector.py    # NEW — 10 cas (CI/SN/BJ + faux positifs)
│   │   │   ├── test_lang_check.py      # NEW
│   │   │   ├── test_circuit_breaker.py # NEW — 5 cas
│   │   │   ├── test_budget.py          # NEW
│   │   │   ├── test_tool_status.py     # NEW
│   │   │   └── test_loop_detector.py   # NEW
│   ├── integration/
│   │   ├── admin/
│   │   │   ├── test_agent_tools_router.py     # NEW — disable/enable/list
│   │   │   └── test_agent_metrics_consolidated.py  # NEW — 6 sections
│   │   └── agent/
│   │       ├── test_runner_loop_detection.py  # NEW
│   │       ├── test_minimal_mode.py            # NEW
│   │       └── test_circuit_breaker_e2e.py    # NEW — flow réel openrouter mock
│   ├── e2e/                            # NEW DIR si absent
│   │   ├── test_agent_e2e_guardrails.py       # NEW — flow complet (anti-injection + PII + budget)
│   │   ├── test_agent_e2e_kill_switch.py      # NEW — admin disable → tool exclu < 1 min
│   │   ├── test_agent_e2e_minimal_mode.py     # NEW — bascule mode + drain in-flight
│   │   └── test_agent_e2e_eval_smoke.py       # NEW — pipeline scripts/eval_agent.py mode mock
│   └── golden/
│       ├── agent_e2e.jsonl             # NEW — 50 cas (FR-018)
│       └── jailbreak_prompts.jsonl     # NEW — 100 prompts adversariaux publics
└── pyproject.toml                       # UNTOUCHED (déjà 80% coverage gate)

frontend/
├── app/
│   └── pages/
│       └── admin/
│           └── agent/
│               ├── metrics.vue          # NEW — dashboard 6 sections (US9, P2)
│               └── tools.vue            # NEW — UI gestion kill-switch (US4, P2 nice-to-have)
└── tests/
    └── pages/admin/agent/
        ├── metrics.test.ts             # NEW — vitest mount + assertions
        └── tools.test.ts               # NEW

extension/                                # UNTOUCHED — pas d'impact F58
```

**Structure Decision**: Web application Option 2. F58 ajoute un sous-package `app/agent/guardrails/` (7 modules ~150 lignes chacun pour rester < 800 LOC) + nouveau modèle SQLAlchemy + 1 migration. Le frontend admin est livré en 2 pages Vue minimales pour US9 et US4 (P2, optionnelles si charge trop élevée).

## Phase 0 — Research (résumé)

Voir `research.md` pour le détail. Décisions clés :

1. **`langdetect` lib choisie** vs heuristique custom — précision suffisante FR/EN/ES/AR (NFR-002), latence < 5 ms par appel.
2. **Circuit breaker pattern** : implémentation custom in-memory (~80 LOC) plutôt que lib `circuitbreaker` (lib non maintenue depuis 2022, risque sécurité).
3. **PII regex** : compilation au démarrage app (lru_cache), patterns dans constante module séparé `pii_patterns.py` (séparation données/logique).
4. **Hash arguments loop detection** : `hashlib.sha256(json.dumps(args, sort_keys=True))` — évite collisions + reproductible.
5. **Eval mock vs real** : utiliser `unittest.mock.patch` sur `llm_client.complete()` + fixtures JSONL pré-enregistrées pour mock ; mode `real` lit `LLM_API_KEY` depuis env CI secrets.
6. **Slack webhook payload** : format Slack Block Kit standard (sévérité → couleur, fields → markdown table) ; httpx async avec timeout 5s + 1 retry.

## Phase 1 — Design & Contracts (résumé)

### Data model

Voir `data-model.md` pour le détail SQL. Synthèse :

- **Nouvelle table** `agent_tool_status` (8 colonnes) — pas de RLS, accès admin uniquement.
- **Migration ALTER `account`** — ajoute 3 colonnes : `daily_token_quota`, `daily_conversation_quota`, `daily_ocr_analysis_quota`.
- **Migration ALTER `agent_run`** — ajoute 6 colonnes : `injection_detected`, `pii_masked_count`, `language_corrected`, `loop_detected`, `circuit_breaker_open`, `mode`.
- **Aucune nouvelle table compteur tokens** : la consommation par compte/jour est calculée via agrégation `agent_run_step` (où les tokens sont déjà enregistrés en F53–F55) avec une vue matérialisée optionnelle si performance dégradée (post-MVP).

### Contracts

- `contracts/admin-tools.md` — 3 endpoints admin tools (POST disable, POST enable, GET list).
- `contracts/admin-metrics.md` — endpoint consolidé GET /admin/agent/metrics avec 6 sections.
- `contracts/guardrails-api.md` — signatures Python des 5 modules guardrails.
- `contracts/eval-runner.md` — CLI `scripts/eval_agent.py [--mode mock|real] [--threshold 0.75] [--report report.json]` + schéma JSON du rapport.
- `contracts/ops-alerting.md` — interface `send_alert()` + payload Slack Block Kit.

### Quickstart

`quickstart.md` documente :
1. Migration : `cd backend && source .venv/bin/activate && alembic upgrade head`
2. Setup tests : `pytest tests/unit/agent/guardrails/ --cov=app.agent.guardrails --cov-fail-under=85`
3. Golden set en mode mock : `python scripts/eval_agent.py --mode mock`
4. Golden set en mode real (CI nightly) : `LLM_API_KEY=... python scripts/eval_agent.py --mode real --threshold 0.75`
5. Test manuel kill-switch : 3 curl admin (disable/list/enable).
6. Test manuel circuit breaker : injection 3 erreurs via fixture httpx-mock.

### Agent context update

Le pointeur `<!-- SPECKIT START --> ... <!-- SPECKIT END -->` dans CLAUDE.md sera mis à jour vers `specs/058-agent-guardrails-eval/plan.md`.

## Complexity Tracking

> Aucune violation constitutionnelle. F58 renforce P9 (eval gating + résilience).
> Pas de complexité non-justifiée à tracker.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none)    | (n/a)      | (n/a)                               |
