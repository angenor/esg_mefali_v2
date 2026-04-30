# Implementation Plan: F35 — Eval LLM Continue (Golden Set + Post-Processeur + Traçabilité)

**Branch**: `035-eval-llm-postprocess` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/035-eval-llm-postprocess/spec.md`

## Summary

MVP backend très focalisé livrant trois capacités :
1. Un **golden set** versionné (`backend/tests/llm_eval/golden_seed.yaml`, 10–20 cas) + un runner CLI/programmatique qui exécute chaque cas contre le pipeline F14 et produit un rapport (JSON + Markdown) avec métriques (`tool_match_rate`, `payload_partial_match_rate`, `fallback_rate`).
2. Un **post-processeur** appelé après la validation LLM qui détecte (a) les patterns d'énumération de choix dans le texte libre → signal `chips_suggestion` ; (b) les chiffres/seuils sans `cite_source` → signal `unsourced_warning` + écriture dans `unsourced_claim_log` (existant F03).
3. Un **endpoint admin** `POST /api/admin/llm-eval/run` qui exécute le runner et renvoie le rapport JSON.

**Hors-scope MVP (Differred)** : CI gating, golden set 50–100, frontend (`<ChipsSuggestion>`, `<UnsourcedWarning>`), dashboard `/admin/llm-eval`, sync DB↔git.

## Technical Context

**Language/Version**: Python 3.11+ (backend), pas de frontend dans ce MVP.
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.x, PyYAML, pytest.
**Storage**: PostgreSQL (réutilise `unsourced_claim_log` F03). Aucune nouvelle table requise pour MVP.
**Testing**: pytest, couverture ≥ 80 % via `pytest --cov`.
**Target Platform**: backend FastAPI Linux/macOS dev local (.venv).
**Project Type**: web-service (backend uniquement pour ce MVP).
**Performance Goals**: 10 cas exécutés < 30s avec LLM stub en tests ; SC-001 < 60s en local réel.
**Constraints**: pas de modification de schéma DB ; respect RLS ; pas d'écriture en base hors `unsourced_claim_log`.
**Scale/Scope**: 10–20 cas seed, < 10 modules nouveaux.

## Constitution Check

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Le post-processeur **renforce** la règle. | ✅ |
| P2 | Multi-tenant RLS | Pas de nouvelle table. Endpoint via `get_current_admin`. | ✅ |
| P3 | Audit log append-only | Réutilise `unsourced_claim_log` ; emit `audit.record(event_type="llm_eval.run")`. | ✅ |
| P4 | Versioning + snapshot | Non applicable. | ✅ |
| P5 | Money typé | Non applicable. | ✅ |
| P6 | Pivot Indicateur unique | Non applicable. | ✅ |
| P7 | Plateforme fermée intermédiaires | Endpoint admin uniquement. | ✅ |
| P8 | Édition manuelle + sync LLM | Non applicable. | ✅ |
| P9 | Tool-use LLM fiable | Mesure `tool_match_rate` ; comparateur strict. | ✅ |
| P10 | UX bottom sheet | Frontend différé hors MVP. | ⚠ deferred |

### Contraintes techniques

- Aucune modif `pyproject.toml` / `uv.lock`.
- Aucune migration Alembic.

## Project Structure

### Source Code

```text
backend/
├── app/
│   ├── eval/
│   │   ├── golden_loader.py          # NEW: charge YAML golden set
│   │   ├── compare_payload.py        # NEW: comparateur partial match
│   │   ├── eval_runner.py            # NEW: orchestre l'exécution
│   │   └── report.py                 # NEW: génération JSON/Markdown
│   ├── llm/
│   │   ├── post_processor.py         # NEW
│   │   └── postprocess_patterns.yaml # NEW
│   ├── api/routes/
│   │   └── admin_llm_eval.py         # NEW: POST /api/admin/llm-eval/run
│   ├── scripts/run_llm_eval.py       # NEW: CLI
│   └── main.py                       # MODIF: include router
└── tests/
    ├── llm_eval/golden_seed.yaml     # NEW
    └── eval/
        ├── test_compare_payload.py
        ├── test_golden_loader.py
        ├── test_eval_runner.py
        ├── test_post_processor.py
        ├── test_report.py
        └── test_admin_llm_eval.py
```

**Structure Decision**: Web-service (backend uniquement). Tout sous `backend/app/eval/`, `backend/app/llm/post_processor.py`, `backend/app/api/routes/admin_llm_eval.py`. Golden set YAML sous `backend/tests/llm_eval/`. Aucune migration.

## Phase 0 — Recherche / Décisions

- **Eval pipeline target** : runner appelle un callable LLM injecté (stub en tests, OpenRouter en prod via admin endpoint avec `temperature=0`).
- **Mode eval** : transactions DB rollback à la fin de chaque cas (sauf `unsourced_claim_log` désactivable via flag).
- **Patterns post-processeur** : YAML lu au boot, regex compilées via `lru_cache`.
- **Comparateur** : pure Python, pas de dépendance externe.
- **Golden set seed** : 10 cas (ask_qcu, ask_qcm, ask_yes_no, ask_number, show_kpi_card, mutation Profil, fallback texte, chiffre non sourcé).

## Phase 1 — Design / Contrats

### `POST /api/admin/llm-eval/run`

Request : `{ "tags": ["forme_juridique"], "limit": 10 }` (tous champs optionnels).

Response 200 :
```json
{
  "total": 10,
  "passed": 8,
  "failed": 2,
  "metrics": {
    "tool_match_rate": 0.9,
    "payload_partial_match_rate": 0.85,
    "fallback_rate": 0.1
  },
  "cases": [
    { "id": "qcu-forme-juridique", "status": "passed", "reason": null },
    { "id": "kpi-ca", "status": "failed", "reason": "tool_mismatch" }
  ],
  "duration_ms": 12400
}
```

Errors : 401, 403, 500.

### Post-processeur

```python
def post_process(
    response_text: str | None,
    tool_calls: list[dict],
    patterns: PostProcessPatterns,
) -> list[PostProcessSignal]
```

```python
@dataclass(frozen=True)
class PostProcessSignal:
    type: Literal["chips_suggestion", "unsourced_warning"]
    payload: dict[str, Any]
```

### Comparateur

```python
def compare_payload(expected_partial: dict, actual: dict) -> tuple[bool, str | None]
```

Clés supportées : `options_count_min`, `options_count_max`, `options_contain`, `equals`, `regex`.

## Constraints / Gating

- Couverture ≥ 80 % sur les modules nouveaux.
- Pas de migration Alembic.
- Pas de modif fichiers parent interdits.

## Complexity Tracking

Aucun écart par rapport à la constitution.
