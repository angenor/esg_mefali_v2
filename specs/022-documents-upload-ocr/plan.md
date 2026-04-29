# Implementation Plan: F22 — Documents Upload & OCR (entreprise)

**Branch**: `022-documents-upload-ocr` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/022-documents-upload-ocr/spec.md`

## Summary

Livrer le backend MVP pour l'upload, le listing, le téléchargement et la suppression de documents d'entreprise (table `document_entreprise` parallèle à `document_projet` de F12), avec extraction synchrone du texte natif des PDFs via `pypdf`, journal d'audit, RLS multi-tenant, et soft-delete cohérent avec F12. Toutes les capacités lourdes (OCR Tesseract, extraction LLM structurée, embeddings Voyage, audio Whisper, surlignage bbox) sont explicitement reportées.

## Technical Context

**Language/Version**: Python 3.11+ (backend `.venv` local)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (Core via `text()`), Alembic, `pypdf`, Pydantic v2.
**Storage**: PostgreSQL 16 (table `document_entreprise`, RLS via `app.current_account_id`) + filesystem local (dev) via `app/storage/local.py:LocalStorage`.
**Testing**: pytest + httpx TestClient (réutiliser fixtures `backend/tests/conftest.py`), couverture mesurée par `pytest --cov=app/entreprise --cov=app/api/routes/entreprise_documents --cov=app/services/ocr_service`.
**Target Platform**: Serveur Linux/Mac dev ; production Europe ou Afrique de l'Ouest.
**Project Type**: web-service (backend FastAPI + frontend Nuxt 4 séparés).
**Performance Goals**: Upload 5 MB < 5 s ; extraction texte natif PDF 10 pages < 5 s ; rejet validation < 200 ms.
**Constraints**: 25 MB max par fichier, 50 docs max par entreprise, traitement OCR synchrone time-boxé 30 s.
**Scale/Scope**: 100 PME × 10 docs/mois ≈ 1 000 docs/mois.

## Constitution Check

| # | Principle | Gate question | Status |
|---|-----------|--------------|--------|
| P1 | Sourçage anti-hallucination | F22 ne crée pas de donnée factuelle catalogue ; texte extrait = donnée utilisateur. | ✅ |
| P2 | Multi-tenant RLS | `document_entreprise.account_id NOT NULL` + policy `tenant_isolation` (calques `document_projet`). Cross-tenant → 404. | ✅ |
| P3 | Audit log append-only | Création / téléchargement / suppression journalisés via `record_audit` (`source_of_change='manual'`). | ✅ |
| P4 | Versioning + snapshot | Pas de référentiel/critère/candidature dans F22 → N/A. | ✅ |
| P5 | Money typé | Aucune valeur monétaire → N/A. | ✅ |
| P6 | Pivot Indicateur | Aucune valeur ESG → N/A. | ✅ |
| P7 | Plateforme fermée | Endpoints `/me/entreprise/documents` réservés rôle PME via `get_current_pme`. | ✅ |
| P8 | Édition manuelle + sync LLM | Texte OCR jamais affiché brut (NFR-004) ; pas de mutation LLM en F22. | ✅ |
| P9 | Tool-use LLM | Tool `extract_from_document` = DEFERRED. F22 backend pur. | ✅ |
| P10 | UX bottom sheet | Pas de UI livrée par F22. | ✅ (deferred to UI feature) |

Aucune violation. Pas de Complexity Tracking nécessaire.

## Project Structure

### Documentation (this feature)

```text
specs/022-documents-upload-ocr/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── entreprise_documents_api.md
├── checklists/
│   └── requirements.md
├── spec.md
└── tasks.md          # généré par /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── alembic/versions/
│   └── 0015_f22_document_entreprise.py     # NEW migration
├── app/
│   ├── api/routes/
│   │   └── entreprise_documents.py         # NEW routes /me/entreprise/documents
│   ├── entreprise/
│   │   ├── documents_service.py            # NEW upload/list/get/read/delete
│   │   └── documents_validators.py         # NEW MAX_DOCS, mime/size/type validators
│   ├── services/
│   │   └── ocr_service.py                  # NEW extract_text_from_pdf (pypdf, 30s timeout)
│   ├── storage/                            # réutilisé F12
│   ├── audit/                              # réutilisé F04
│   └── main.py                             # +include_router(entreprise_documents)
└── tests/
    ├── api/
    │   └── test_entreprise_documents_api.py
    ├── entreprise/
    │   └── test_documents_service.py
    └── services/
        └── test_ocr_service.py
```

**Structure Decision**: monolithe FastAPI organisé par domaine. F22 ajoute `entreprise/documents_service.py` en miroir exact de `projets/documents_service.py` (F12). Le `OcrService` est placé sous `app/services/` (transverse, prêt à être réutilisé par F12 en post-MVP).

## Phase 0 — Research

Voir [research.md](./research.md). Toutes les NEEDS CLARIFICATION ont été résolues via `/speckit-clarify`. Choix techniques verrouillés :

- `pypdf` pour extraction PDF natif (déjà commun, pas de dépendances natives).
- Soft-delete (`deleted_at`) en miroir de F12 plutôt que hard-delete : cohérence et traçabilité audit.
- Timeout synchrone 30 s : `concurrent.futures.ThreadPoolExecutor.submit(...).result(timeout=30)`.
- Mime sniffing : trust `UploadFile.content_type` + whitelist stricte ; pas de python-magic en MVP.

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md) — schéma `document_entreprise` + transitions d'état OCR.
- [contracts/entreprise_documents_api.md](./contracts/entreprise_documents_api.md) — endpoints, requêtes, réponses, codes d'erreur.
- [quickstart.md](./quickstart.md) — comment tester localement.

## Phase 2 — Tasks (out of scope here)

Sera généré par `/speckit-tasks`.
