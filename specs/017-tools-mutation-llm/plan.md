# Implementation Plan: F17 — Tools de Mutation LLM

**Feature**: F17 — Tools de mutation LLM
**Branch**: `017-tools-mutation-llm`
**Status**: Approved
**Date**: 2026-04-29

## Architecture Overview

F17 ajoute une couche **mutation tools** s'appuyant sur les services métier existants (F11 entreprise, F12 projets/candidatures), respectant : audit log (F04), RLS (F02), tool registry (F14), confirmation destructive via `ask_yes_no` (F15).

### Pattern d'exécution

```
LLM tool call ──► tool handler (decorated @tool, @destructive?, @rate_limited)
                  │
                  ├─► Pydantic validation (extra='forbid', FK existence)
                  ├─► @destructive : si confirmed=False → MutationConfirmationRequired
                  ├─► appel service métier F11/F12 avec source_of_change=LLM
                  │   (les services loggent déjà audit_log + EventBus)
                  └─► retour résultat structuré
```

### Décorateurs F17 (nouveaux)

- **`@destructive`** : intercepte avant exécution. Si `confirmed=False`, retourne `MutationConfirmationRequired` (`requires_confirmation=True`, `message`, `impact`, `tool`).
- **`@rate_limited(max_per_min=10)`** : in-process token bucket par user, lève `RateLimitExceeded` (HTTP 429).

> `@audited` n'est pas un nouveau décorateur dédié en MVP : les services F11/F12 loggent déjà avec `source_of_change=LLM`. Le décorateur F04 `journal_llm_mutation` existe (non utilisé directement ici car redondant) — point d'extension pour US7-US9 P2.

### Tools P1 MVP livrés

| Tool | Service | Audit |
|------|---------|-------|
| `update_company_profile(fields)` | `entreprise.service.update_partial` | OK F11 |
| `create_project(fields)` | `projets.service.create_projet` | OK F12 |
| `update_project(id, fields)` | `projets.service.update_projet` | OK F12 |
| `delete_project(id, confirmed)` (destructif) | `projets.service.delete_projet` | OK F12 |
| `create_candidature(project_id, offre_id)` | `projets.service.create_candidature` | OK F12 |
| `update_candidature_status(id, status)` | `projets.service.update_candidature_status` | OK F12 |
| `delete_candidature(id, confirmed)` (destructif) | `projets.service.delete_candidature` | OK F12 |

### Tools P2 [DEFERRED]

- `attach_document` (dépend F22 OCR/upload) — DEFERRED
- `recompute_score` (dépend F23) — DEFERRED
- `generate_attestation` / `revoke_attestation` (dépend F30) — DEFERRED
- `generate_dossier` (dépend F26) — DEFERRED
- Endpoint `POST /me/audit-log/{id}/revert` (US10 UNDO) — DEFERRED

### Garde-fou catalogue (US5)

`register_mutation_tools()` enregistre uniquement les tools entreprise/projet/candidature. Aucun tool catalogue n'est exposé. Test `test_registry_no_catalog.py` vérifie l'absence des noms `update_referentiel`, `update_fonds`, `update_offre`, `update_intermediaire`, `update_indicateur`, `update_source`, `update_skill`, `update_template`.

### Rate limiting (FR-010)

In-process : `dict[user_id, deque[ts]]` + lock thread-safe. 10 mutations / 60s glissantes. 11ᵉ → `RateLimitExceeded` → 429.

### Cross-tenant (SC-003)

Le service `projets.service` accepte `account_id` ; l'appel échoue (`ProjetNotFound`) si l'ID ne lui appartient pas. Le tool handler reçoit `account_id` du `current_user`, jamais du payload LLM.

## Composants à créer

### Backend (P1 MVP)

```
backend/app/orchestrator/tools/mutations/
├── __init__.py                       # register_mutation_tools()
├── _destructive.py                   # @destructive + MutationConfirmationRequired
├── _rate_limit.py                    # @rate_limited + RateLimitExceeded
├── _common.py                        # MutationContext dataclass + helpers
├── update_company_profile.py
├── create_project.py
├── update_project.py
├── delete_project.py
├── create_candidature.py
├── update_candidature_status.py
└── delete_candidature.py

backend/app/api/routes/llm_mutations.py   # POST /me/llm-tools/mutations/{name}
```

### Tests

```
backend/tests/orchestrator/tools/mutations/
├── test_destructive.py
├── test_rate_limit.py
├── test_registry_no_catalog.py       # SC-005
├── test_update_company_profile.py    # US1
├── test_create_project.py            # US2
├── test_update_project.py            # US2
├── test_delete_project.py            # US2 + US4
├── test_create_candidature.py        # US3
├── test_update_candidature_status.py # US3
├── test_delete_candidature.py        # US3 + US4
└── test_cross_tenant.py              # SC-003
```

## Hors-scope MVP

- US6-US10 (P2) : tools dépendant de features non livrées.
- Frontend (bandeau UNDO, intégration chat).
- Rate limiter distribué (Redis post-MVP).

## Risques

- **Validation FK existence** : possible ralentissement. MVP : RLS DB (`ProjetNotFound` 404) suffit.
- **Confirmation destructive bypass** : test e2e explicite NFR-003.
- **Service candidatures** : la logique candidatures est dans `app/projets/service.py` (vérifier helpers existants ou créer). Si absent → fallback inline minimal.

## Dépendances vérifiées

- F04 `record_audit` + `SourceOfChange.LLM` : OK (`backend/app/audit/helper.py:39`).
- F11 `update_partial(source_of_change=...)` : OK (`backend/app/entreprise/service.py:286`).
- F12 `create_projet/update_projet/delete_projet(source_of_change=...)` : OK.
- F14 `tool_registry.tool()` + `extra='forbid'` enforcement : OK (`backend/app/orchestrator/tool_registry.py:36`).
- F15 `ask_yes_no` : OK.
