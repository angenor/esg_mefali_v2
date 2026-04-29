# Tasks — F22 Documents Upload & OCR (entreprise)

**Feature**: F22 — Documents Upload & OCR (entreprise)
**Branch**: `022-documents-upload-ocr`
**Mode**: TDD strict (tests RED → impl GREEN → refactor)

## Phase 1 — Setup

- [ ] T001 Vérifier la présence de `pypdf` dans `backend/requirements.txt` ; ajouter `pypdf>=4.0` si manquant et installer dans `.venv` (sans modifier `pyproject.toml`)
- [ ] T002 [P] Créer le squelette des dossiers manquants : `backend/app/services/`, `backend/tests/api/`, `backend/tests/entreprise/`, `backend/tests/services/` (avec `__init__.py` si convention)

## Phase 2 — Foundational (blocking)

- [ ] T010 Créer la migration Alembic `backend/alembic/versions/0015_f22_document_entreprise.py` (table `document_entreprise` + indexes + GRANT + RLS policy `tenant_isolation` + CHECK contraintes — voir data-model.md). Down revision = `0014_f19_skill`
- [ ] T011 Appliquer la migration localement : `alembic upgrade head` ; vérifier `\d document_entreprise` en psql
- [ ] T012 [P] Créer `backend/app/entreprise/documents_validators.py` avec : constantes `MAX_DOCS_PER_ENTREPRISE=50`, `MAX_FILE_BYTES=25*1024*1024`, sets `MIME_WHITELIST` et `DOC_TYPES`, classe `ValidationError(code, message)`, fonctions `validate_mime`, `validate_size`, `validate_doc_type`

## Phase 3 — US1 : Upload & isolation par compte (P1)

**Goal**: Endpoint POST + service upload, isolation account_id, audit log.

**Independent test**: tests d'intégration HTTP POST + listing + cross-tenant.

### Tests RED

- [ ] T100 [P] [US1] Écrire `backend/tests/entreprise/test_documents_service.py` (RED) : `test_upload_creates_row_and_audit`, `test_upload_too_large_raises`, `test_upload_bad_mime_raises`, `test_upload_bad_doc_type_raises`, `test_upload_max_50_raises_too_many`, `test_upload_without_entreprise_raises`
- [ ] T101 [P] [US1] Écrire `backend/tests/api/test_entreprise_documents_api.py` (RED) : `test_post_upload_201`, `test_post_upload_413_size`, `test_post_upload_415_mime`, `test_post_upload_409_too_many`, `test_post_upload_400_no_entreprise`, `test_cross_tenant_get_returns_404`

### Implementation GREEN

- [ ] T110 [US1] Créer `backend/app/entreprise/documents_service.py` : dataclass `DocumentEntrepriseRow`, exceptions `EntrepriseRequired`, `DocumentNotFound`, `TooManyDocuments`, helper `_resolve_entreprise_id(db, account_id)`, fonction `upload_document(...)` (INSERT + audit `record_audit` + storage path `entreprise/{account_id}/{entreprise_id}/{id}.{ext}`)
- [ ] T111 [US1] Créer `backend/app/api/routes/entreprise_documents.py` : `APIRouter(prefix="/me/entreprise", tags=["entreprise-documents"])`, endpoint `POST /documents` mappant les exceptions vers HTTP 400/409/413/415/422 (calque `app/api/routes/projets_documents.py`)
- [ ] T112 [US1] Inclure le router dans `backend/app/main.py` via `app.include_router(entreprise_documents.router)` (ajout d'une seule ligne)

### Refactor

- [ ] T120 [US1] Lancer `pytest tests/entreprise/test_documents_service.py tests/api/test_entreprise_documents_api.py -v` → tous verts ; couverture ≥ 80% sur le nouveau code

## Phase 4 — US2 : Listing, download, delete (P1)

**Goal**: GET listing, GET détail, GET download, DELETE soft.

**Independent test**: cycle upload → list → download bytes match → delete → list vide.

### Tests RED

- [ ] T200 [P] [US2] Étendre `backend/tests/entreprise/test_documents_service.py` (RED) : `test_list_documents_returns_only_account`, `test_get_document_cross_tenant_404`, `test_read_document_returns_bytes`, `test_delete_soft_deletes_and_calls_storage`, `test_delete_idempotent_on_already_deleted`
- [ ] T201 [P] [US2] Étendre `backend/tests/api/test_entreprise_documents_api.py` (RED) : `test_get_list_200`, `test_get_detail_200`, `test_get_download_200_returns_bytes`, `test_delete_204`, `test_delete_then_list_empty`, `test_delete_audit_event_recorded`

### Implementation GREEN

- [ ] T210 [US2] Étendre `backend/app/entreprise/documents_service.py` avec `list_documents(db, account_id)`, `get_document(db, doc_id, account_id)`, `read_document(db, storage, doc_id, account_id)`, `delete_document(db, storage, doc_id, account_id, user_id)` (soft-delete `deleted_at = now()` + `storage.delete(...)` best-effort + `record_audit` notes `document_entreprise.deleted` / `.downloaded`)
- [ ] T211 [US2] Étendre `backend/app/api/routes/entreprise_documents.py` : endpoints `GET /documents`, `GET /documents/{doc_id}`, `GET /documents/{doc_id}/download`, `DELETE /documents/{doc_id}`

### Refactor

- [ ] T220 [US2] Vérifier la cohérence des codes d'erreur avec `contracts/entreprise_documents_api.md` ; suite verte

## Phase 5 — US3 : Extraction texte natif PDF (P1)

**Goal**: OcrService synchrone time-boxé 30s ; remplit `text_content` et `ocr_status` à l'upload.

**Independent test**: PDF natif → `done`+text ; JPG/.docx/.xlsx → `deferred` ; PDF sans texte → `deferred`.

### Tests RED

- [ ] T300 [P] [US3] Créer `backend/tests/services/test_ocr_service.py` (RED) : `test_extract_pdf_with_native_text_returns_text`, `test_extract_pdf_without_text_returns_empty`, `test_extract_pdf_corrupt_raises`, `test_extract_timeout_raises_timeout_error` (timeout très court via paramètre injecté)
- [ ] T301 [P] [US3] Étendre `backend/tests/api/test_entreprise_documents_api.py` (RED) : `test_post_pdf_native_sets_ocr_done`, `test_post_jpg_sets_ocr_deferred`, `test_post_docx_sets_ocr_deferred`, `test_post_xlsx_sets_ocr_deferred`, `test_get_detail_exposes_ocr_status_and_error`

### Implementation GREEN

- [ ] T310 [US3] Créer `backend/app/services/ocr_service.py` : `extract_text_from_pdf(data: bytes, *, timeout_s: float = 30.0) -> str` (ThreadPoolExecutor + `pypdf.PdfReader`, retourne "" si pas de texte, lève `TimeoutError`) ; `extract_text(mime: str, data: bytes) -> tuple[str, str|None, str|None]` retournant `('done', text, None)` / `('deferred', None, msg)` / `('failed', None, err)`
- [ ] T311 [US3] Étendre `backend/app/entreprise/documents_service.py:upload_document` : après INSERT pending, exécuter `extract_text(mime, data)` et UPDATE `ocr_status`, `text_content`, `ocr_error`
- [ ] T312 [US3] Étendre les payloads API pour inclure `ocr_status` et `ocr_error` (POST 201, GET listing, GET détail)

### Refactor

- [ ] T320 [US3] `pytest -q tests/services/test_ocr_service.py tests/entreprise tests/api/test_entreprise_documents_api.py --cov=app/entreprise --cov=app/api/routes/entreprise_documents --cov=app/services/ocr_service` → ≥ 80% ; `ruff check` propre

## Phase 6 — Polish & cross-cutting

- [ ] T900 [P] Vérifier non-régression F01–F21 : `pytest -q backend/tests/`
- [ ] T901 [P] Logger les manuel-tests dans `.cc-runtime/logs/manual-tests-22.md` (résumé curl + attendus repris du quickstart)
- [ ] T902 Rapport de couverture finale
- [ ] T903 Vérifier que `note.md`, `.cc-deps.json`, `.cc-queue.md`, `.cc-orchestrator.md` ne sont PAS modifiés par F22

## Dependencies

- T001–T002 (Setup) avant tout.
- T010 → T011 → T012 (Foundational) avant Phase 3+.
- Phase 3 (US1) avant Phase 4 (US2).
- Phase 5 (US3) peut commencer après US1 ; T311 dépend de T110.
- Phase 6 après tous les US verts.

## Parallel opportunities

- T100 ∥ T101 ; T200 ∥ T201 ; T300 ∥ T301 ; T900 ∥ T901.

## MVP scope

US1 + US2 + US3 (toutes P1) = MVP livrable F22. Pas de scope partiel volontaire.
