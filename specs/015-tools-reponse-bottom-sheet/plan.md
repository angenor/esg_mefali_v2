# Implementation Plan: Tools de Réponse en Bottom Sheet (F15)

**Branch**: `015-tools-reponse-bottom-sheet` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/015-tools-reponse-bottom-sheet/spec.md`

## Summary

Livrer 11 tools de réponse (`ask_*`, `show_form`, `show_summary_card`) avec schémas Pydantic stricts enregistrés dans le `tool_registry` F14.

**Approche pragmatique MVP** :
1. Backend (P1) : créer `app/orchestrator/tools/` avec un module par tool, schémas Pydantic `extra='forbid'`, et `register_response_tools()` appelée au startup `main.py`.
2. Backend (P1) : retirer `ask_qcu`/`ask_yes_no`/`show_summary_card` de `fixtures_tools.py` (schémas pauvres) ; les redéfinir richement dans le nouveau package F15.
3. Tests TDD ≥ 80 % sur `app/orchestrator/tools/`.
4. Frontend bottom sheet : **DEFERRED** (livraison partielle backend-only).

## Technical Context

**Language/Version** : Python 3.11 (backend) ; TypeScript Nuxt 4 (frontend, deferred).
**Primary Dependencies** : FastAPI, Pydantic v2, pytest, ruff.
**Storage** : PostgreSQL — colonne `chat_message.payload_json` (JSONB) déjà créée par F13.
**Testing** : pytest + pytest-cov ; ruff lint.
**Target Platform** : backend Linux/macOS local.
**Project Type** : web-service multi-tenant.
**Performance Goals** : validation payload < 5 ms.
**Constraints** : RLS account_id (F02), audit log F04, aucune nouvelle table.
**Scale/Scope** : 11 tools, ~7 livrés MVP P1, ~4 P2 deferrable.

## Constitution Check

| # | Principe | Statut |
|---|----------|--------|
| P1 | Sourçage anti-hallucination — F15 ne crée pas de données factuelles. | ✅ N/A |
| P2 | RLS account_id — hérité F13. | ✅ |
| P3 | Audit log — hérité F13/F04. | ✅ |
| P4 | Versioning — pas de référentiels. | ✅ N/A |
| P5 | Money typé — `ask_number.money={currency}`. | ✅ |
| P6 | Pivot Indicateur unique — pas d'écriture indicateur. | ✅ N/A |
| P7 | Plateforme fermée — pas de rôle externe. | ✅ |
| P8 | Édition manuelle + sync LLM — bascule libre garantie. | ✅ |
| P9 | Tool-use LLM fiable — `extra='forbid'`, use_when/dont_use_when. | ✅ |
| P10 | UX bottom sheet — règle imposée par spec. | ✅ |

## Project Structure

```text
specs/015-tools-reponse-bottom-sheet/
├── plan.md
├── spec.md
├── tasks.md
├── checklists/requirements.md
└── contracts/tools-schemas.md
```

### Backend

```text
backend/app/orchestrator/
├── tool_registry.py        # F14 — inchangé
├── fixtures_tools.py       # F14 — épuré : retire ask_qcu/ask_yes_no/show_summary_card
└── tools/                  # NOUVEAU package F15
    ├── __init__.py         # register_response_tools()
    ├── _common.py          # Option, helpers
    ├── ask_qcu.py
    ├── ask_qcm.py
    ├── ask_yes_no.py
    ├── ask_select.py
    ├── ask_number.py
    ├── ask_file_upload.py
    ├── show_summary_card.py
    ├── ask_date.py         # P2 — peut être DEFERRED
    ├── ask_rating.py       # P2 — peut être DEFERRED
    └── show_form.py        # P2 — peut être DEFERRED

backend/app/main.py         # appel register_response_tools() au startup
```

### Frontend (DEFERRED)

```text
frontend/app/components/chat/   # NON LIVRÉ DANS LE MVP F15
```

### Tests

```text
backend/tests/tools/
├── conftest.py
├── test_ask_qcu.py
├── test_ask_qcm.py
├── test_ask_yes_no.py
├── test_ask_select.py
├── test_ask_number.py
├── test_ask_file_upload.py
├── test_show_summary_card.py
└── test_register_response_tools.py
```

## Phase 0 — Research

- F13 : `chat_message.payload_json` JSONB + `payload_json` accepté par POST /me/chat/threads/{id}/messages → **disponible** (cf. `app/chat/schemas.py:59,74`).
- F14 : `tool_registry.tool()` impose `extra='forbid'` → **disponible**.
- Conflit : `fixtures_tools.py` enregistre déjà les noms `ask_qcu`/`ask_yes_no`/`show_summary_card`. Solution : déplacer ces 3 entrées vers `app/orchestrator/tools/` avec schémas riches ; mettre à jour `test_payload_validator.py`, `test_tool_selector.py` pour utiliser les nouveaux payloads.

## Phase 1 — Design

### Schémas Pydantic

- `Option` : `{value: str, label: str, description: str | None}`.
- `AskQcuPayload` : `{question, options: list[Option](2..7), allow_other: bool=False}`.
- `AskQcmPayload` : `{question, options, min_select?, max_select?}`.
- `AskYesNoPayload` : `{question, yes_label='Oui', no_label='Non'}`.
- `AskSelectPayload` : `{question, options? | options_endpoint?, multi=False}` + validator XOR.
- `AskNumberPayload` : `{question, unit, min?, max?, step?, money?: {currency: Literal['XOF','EUR']}}`.
- `AskDatePayload` / `AskDateRangePayload` (P2).
- `AskRatingPayload` (P2) : `{question, scale: Literal['1-5','1-10']}`.
- `AskFileUploadPayload` : `{question, attach_to: {entity_type: Literal['projet','entreprise'], entity_id?: UUID}, accepted_mime: list[str], max_size_mb}`.
- `ShowFormPayload` (P2) : `{title, fields: list[FormField], submit_label?}`.
- `ShowSummaryCardPayload` : `{title, fields: list[{label, value, source?}], actions: list[{label, kind: Literal['confirm','edit','cancel']}]}`.

### Sécurité

Sanitisation backend : `StringConstraints(strip_whitespace=True, max_length=512)` + ban des balises `<` `>` dans `label`/`description`. Sanitize HTML approfondie côté frontend (deferred).

### Validation client miroir

Reportée itération 2 (génération zod depuis OpenAPI).

## Phase 2 — Tasks (voir tasks.md)
