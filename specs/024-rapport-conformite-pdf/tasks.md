# Tasks — F24 Rapport Conformité PDF (MVP)

## T1 — Dependencies
- Ajouter `reportlab>=4.0,<5` et `matplotlib>=3.8,<4` à `backend/requirements.txt`.

## T2 — Migration table rapport_genere
- Créer `backend/alembic/versions/0017_f24_rapport_genere.py` (calque F23 RLS).

## T3 — Radar (TDD)
- Test `tests/rapports/test_radar.py` (PNG header, bytes non vides).
- Implémenter `app/rapports/radar.py::render_radar_png`.

## T4 — PDF builder (TDD)
- Test `tests/rapports/test_pdf_builder.py` (bytes commencent par %PDF-, contient nom PME).
- Implémenter `app/rapports/pdf_builder.py::build_pdf`.

## T5 — Schemas pydantic
- `app/rapports/schemas.py` (RapportCreateIn, RapportOut, RapportListOut).

## T6 — Service (TDD avec DB)
- Test `tests/rapports/test_service.py` (génère, persiste, audit, snapshot).
- Implémenter `app/rapports/service.py::generate_rapport`, `list_rapports`, `get_rapport`.

## T7 — Router (TDD avec TestClient)
- Test `tests/rapports/test_router.py` (POST 201, GET list, GET download).
- Implémenter `app/rapports/router.py`.

## T8 — Wiring main.py
- Ajouter `include_router(rapports_router)` dans `backend/app/main.py`.

## T9 — Manual tests log
- Documenter dans `.cc-runtime/logs/manual-tests-24.md`.
