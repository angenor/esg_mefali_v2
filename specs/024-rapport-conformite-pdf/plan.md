# Implementation Plan — F24 Rapport Conformité PDF (MVP)

**Branch**: `024-rapport-conformite-pdf` | **Date**: 2026-04-29
**Spec**: [spec.md](./spec.md)

## Technical Context

**Language**: Python 3.11+ backend (FastAPI + SQLAlchemy 2.x + Alembic).
**New deps**: `reportlab>=4.0,<5`, `matplotlib>=3.8,<4`.
**Storage**: Postgres (table `rapport_genere`) + filesystem (PDF bytes).
**Testing**: pytest + pytest-asyncio + httpx (TestClient).

## Modules

```
backend/app/rapports/
  __init__.py
  service.py        # generate_rapport(...) orchestrator
  pdf_builder.py    # reportlab platypus story builder
  radar.py          # matplotlib radar PNG renderer
  schemas.py        # pydantic v2
  router.py         # /me/rapports/* endpoints
backend/alembic/versions/
  0017_f24_rapport_genere.py
backend/tests/rapports/
  __init__.py
  test_radar.py
  test_pdf_builder.py
  test_service.py
  test_router.py
```

## Phases

### Phase 0 — research

- Décision : reportlab (pur Python) > weasyprint (deps natives) pour MVP macOS-friendly.
- Décision : matplotlib Agg backend > chart.js server-side (pas de Node).
- Décision : stockage fichier filesystem local (pas S3 pour MVP).

### Phase 1 — schéma & migration

- Migration `0017_f24_rapport_genere.py` (création table + index lookup + RLS).

### Phase 2 — radar (TDD)

- `radar.py::render_radar_png(scores_by_pillar) -> bytes`.
- Test : pas d'exception, bytes non vides, header PNG.

### Phase 3 — pdf_builder (TDD)

- `pdf_builder.py::build_pdf(payload) -> bytes`.
- Sections : couverture, score par référentiel, lacunes, annexe sources.
- Test : pdf bytes start with `%PDF-`.

### Phase 4 — service (TDD)

- `service.py::generate_rapport(...)` orchestre : load scores F23 -> build payload -> render radar -> build PDF -> write file -> INSERT rapport_genere -> record_audit.

### Phase 5 — router (TDD)

- `POST /me/rapports/conformite`
- `GET /me/rapports`
- `GET /me/rapports/{id}/download`

### Phase 6 — wiring

- `app/main.py` include_router.

## Risques

- reportlab + matplotlib en mémoire : OK MVP.
- pas de Jinja2 : layout en Python, verbeux mais OK pour MVP.
- RLS test : couvert par fixture conftest existante.

## Constitution Check

Voir spec.md "Constitution gates". Tous les gates passent.
