# Implementation Plan: Source & Sourçage Anti-Hallucination

**Branch**: `003-source-anti-hallucination` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/003-source-anti-hallucination/spec.md`

## Summary

F03 livre le **cœur structurel et applicatif de l'invariant Module 0** (sourcing obligatoire). On pose : (1) une entité `source` avec workflow `pending → verified → outdated/rejected`, double validation, embedding `vector(1024)`, FK NOT NULL préparée pour toutes les entités catalogue ; (2) trois opérations backend `cite_source`, `search_source`, `flag_unsourced` prêtes à être exposées en function-calling OpenRouter ; (3) un middleware FastAPI qui rejette toute sortie LLM contenant un chiffre ESG sans tool-call `cite_source` valide vers une source `verified`, avec retry plafonné à 2 et message d'échappatoire ; (4) un composant Nuxt `<SourceCite>` rendant un picto cliquable ouvrant un bottom sheet ; (5) un utilitaire backend `build_sources_appendix` ; (6) une table `unsourced_claim_log` + endpoint admin agrégé sous RLS. Le LLM lui-même reste Phase 3 ; cette feature livre les contrats que la Phase 3 consommera sans modification.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5 / Vue 3 / Nuxt 4 (frontend)
**Primary Dependencies**: FastAPI, Pydantic v2 (`extra='forbid'`), SQLAlchemy 2 + Alembic, asyncpg, pgvector-python, httpx (Voyage), cachetools (TTL cache middleware) ; Nuxt 4, Pinia, TailwindCSS v4, gsap (bottom sheet), `@iconify/vue` (picto)
**Storage**: PostgreSQL 16 + extension `pgvector` (image `pgvector/pgvector:pg16`, seul service dockerisé). Index GIN tsvector + IVFFlat vector(1024). RLS héritée de F02.
**Testing**: pytest (unit + integration backend), Vitest (unit composant Nuxt), Playwright (E2E bottom sheet — à minima démo) ; eval set 20 cas pour le middleware (livrable test, sera étendu à 50 par F35).
**Target Platform**: Backend Linux (FastAPI Uvicorn) + Postgres dockerisé en dev ; frontend SSR/SPA Nuxt 4 ; navigateurs modernes.
**Project Type**: Web application (backend FastAPI + frontend Nuxt) — structure existante.
**Performance Goals**: `search_source` p95 < 200ms sur 5000 sources `verified` (NFR-001 / SC-005) ; middleware < 50ms p95 (NFR-002 / SC-006).
**Constraints**: Aucun secret hardcodé (`VOYAGE_API_KEY`, `LLM_*` via `.env`) ; FCFA-EUR peg 655.957 si une Source décrit un montant ; français par défaut.
**Scale/Scope**: 5000 sources `verified` au catalogue cible, ~50 entrées `unsourced_claim_log` / jour / tenant en pic, ~20 retries middleware / heure / tenant.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Cette feature **est** P1 incarné. `source.verification_status`, FK `source_id NOT NULL`, vues `v_<entity>_verified`, middleware tool-call `cite_source`. | ✅ |
| P2 | Multi-tenant RLS | `unsourced_claim_log` porte `account_id NOT NULL` + politique RLS via `app.account_id` (réutilise mécanisme F02). `source` est catalogue global lecture publique unitaire (FR-004), recherche admin sous RBAC F02. Cross-tenant → 404. | ✅ |
| P3 | Audit log append-only | Transitions de statut Source (pending→verified, verified→outdated…) tracées via insertion structurée (consommée par F04). `source_of_change` = `admin` ou `system` (embedding). | ✅ |
| P4 | Versioning + snapshot candidatures | `source` porte `version` (texte libre du référentiel) et `date_publi`. La feature ne crée pas de candidature ; pas de `snapshot_json` à introduire ici. | ✅ |
| P5 | Money typé | Aucune valeur monétaire introduite par la feature (la Source décrit un montant, ne le persiste pas typé). | ✅ |
| P6 | Pivot Indicateur unique | Aucune valeur ESG PME introduite ; les vues `v_<entity>_verified` couvrent toutes les entités catalogue (Indicateur en tête) sans dupliquer par axe E/S/G. | ✅ |
| P7 | Plateforme fermée aux intermédiaires | Aucun rôle `Intermediaire` introduit. Seuls PME (lecture picto) et Admin (gestion catalogue) consomment. | ✅ |
| P8 | Édition manuelle + sync LLM | Le LLM peut citer mais pas créer/modifier une Source ; la création/validation est manuelle (admin). Pas de champ LLM-only en lecture seule. | ✅ |
| P9 | Tool-use LLM fiable | 3 tools nommés verbalement (`cite_source`, `search_source`, `flag_unsourced`), schémas Pydantic `extra='forbid'`, "use when / don't use when" dans docstrings, retry max 2 dans middleware, eval set 20 cas (extension F35). | ✅ |
| P10 | UX bottom sheet | `<SourceCite>` ouvre la liste des sources dans un bottom sheet animé gsap, jamais inline. Pas de saisie utilisateur dans la bulle LLM. | ✅ |

**Verdict GATE Phase 0** : ✅ Tous les gates passent. Aucun écart, aucun `Complexity Tracking` requis.

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ; LLM via OpenRouter ; embeddings Voyage `voyage-3.5` (1024 dim).
- Dev local : backend `.venv`, Postgres seul service dockerisé.
- Hébergement production : Europe ou Afrique de l'Ouest uniquement.
- Conformité : RGPD + loi ivoirienne 2013-450 + UEMOA 20/2010.
- Langue : français par défaut.

## Project Structure

### Documentation (this feature)

```text
specs/003-source-anti-hallucination/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI excerpts + Pydantic tool schemas + Vue prop contract)
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── alembic/
│   └── versions/
│       └── 003_source_table_and_unsourced_log.py   # Migration : table source + unsourced_claim_log + vues v_*_verified + RLS + index GIN/IVFFlat
├── app/
│   ├── models/
│   │   ├── source.py                                # SQLAlchemy : Source + enum verification_status
│   │   └── unsourced_claim_log.py
│   ├── schemas/
│   │   └── source.py                                # Pydantic v2 strict (extra='forbid')
│   ├── services/
│   │   ├── source_service.py                        # CRUD admin + transitions de statut + recompute embedding
│   │   ├── embedding_service.py                     # Wrapper Voyage AI voyage-3.5 (déjà posé en F01)
│   │   ├── llm_tools/
│   │   │   ├── cite_source.py                       # Tool handler
│   │   │   ├── search_source.py                     # Tool handler (full-text + vector hybride)
│   │   │   └── flag_unsourced.py                    # Tool handler
│   │   └── llm_validation/
│   │       ├── middleware.py                        # validate_llm_output()
│   │       ├── heuristics.py                        # Détection chiffre+unité ESG
│   │       └── decision_cache.py                    # TTLCache 5 min + bust on status change
│   ├── api/
│   │   ├── routes/
│   │   │   ├── sources.py                           # GET /sources, GET /sources/{id}
│   │   │   └── admin_unsourced.py                   # GET /admin/unsourced-claims (agrégé, RLS)
│   │   └── deps.py                                  # account_id middleware (F02)
│   ├── utils/
│   │   └── sources_appendix.py                      # build_sources_appendix(ids) -> markdown + to_pdf_section
│   └── prompts/
│       └── system_anti_hallucination.md             # Template prompt non-négociable Module 0.1
└── tests/
    ├── unit/
    │   ├── test_source_service.py
    │   ├── test_heuristics.py
    │   ├── test_decision_cache.py
    │   ├── test_sources_appendix.py
    │   └── test_llm_tools.py
    ├── integration/
    │   ├── test_sources_routes.py
    │   ├── test_admin_unsourced_routes.py
    │   ├── test_middleware_retry.py
    │   └── test_rls_unsourced.py
    └── eval/
        └── llm_anti_hallucination_set.json          # 20 cas (extensible F35)

frontend/
├── app/
│   ├── components/
│   │   └── source/
│   │       ├── SourceCite.vue                       # Picto + ouverture bottom sheet
│   │       └── SourceListBottomSheet.vue            # Liste sources (gsap)
│   ├── composables/
│   │   └── useSourceFetch.ts                        # GET /sources/{id}
│   └── pages/
│       └── demo/
│           └── source-cite-demo.vue                 # Page démo SC-003
└── tests/
    ├── unit/
    │   └── SourceCite.spec.ts                       # Vitest
    └── e2e/
        └── source-cite.spec.ts                      # Playwright (3 états)
```

**Structure Decision**: Web application existante (backend FastAPI + frontend Nuxt 4). On n'introduit ni nouveau projet ni nouveau service. Toute la couche middleware LLM vit en backend ; le composant UI vit dans `frontend/app/components/source/` (kebab-case) selon les conventions Nuxt 4.

## Complexity Tracking

> Aucun écart à la constitution. Section vide.
