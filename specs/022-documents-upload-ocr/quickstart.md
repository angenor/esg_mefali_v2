# Quickstart — F22 Documents Upload & OCR

## Prérequis

- Backend `.venv` activé, Postgres dockerisé up.
- Migration `0015_f22_document_entreprise` appliquée (`alembic upgrade head`).
- Une PME authentifiée avec une entreprise enregistrée (F11).

## Lancer les tests

```bash
cd backend
.venv/bin/pytest -q tests/api/test_entreprise_documents_api.py \
                   tests/entreprise/test_documents_service.py \
                   tests/services/test_ocr_service.py \
                   --cov=app/entreprise --cov=app/api/routes/entreprise_documents \
                   --cov=app/services/ocr_service --cov-report=term-missing
.venv/bin/ruff check app/entreprise app/api/routes/entreprise_documents.py app/services/ocr_service.py
```

## Smoke test manuel (curl)

```bash
TOKEN=...    # JWT PME
BASE=http://localhost:8000

# Upload
curl -X POST "$BASE/me/entreprise/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -F file=@/path/to/statuts.pdf \
  -F type=statuts

# Listing
curl "$BASE/me/entreprise/documents" -H "Authorization: Bearer $TOKEN"

# Détail
curl "$BASE/me/entreprise/documents/<doc_id>" -H "Authorization: Bearer $TOKEN"

# Download
curl -o /tmp/back.pdf "$BASE/me/entreprise/documents/<doc_id>/download" \
  -H "Authorization: Bearer $TOKEN"

# Delete
curl -X DELETE "$BASE/me/entreprise/documents/<doc_id>" \
  -H "Authorization: Bearer $TOKEN"
```

## Vérifications DB rapides

```sql
SELECT id, name, ocr_status, ocr_error, created_at
FROM document_entreprise
WHERE deleted_at IS NULL AND account_id = '...';

SELECT entity_type, entity_id, notes, created_at
FROM audit_log
WHERE entity_type = 'document_entreprise'
ORDER BY created_at DESC LIMIT 10;
```

## Cas de test couverts

| Scénario | Cas | Résultat attendu |
|---------|-----|------------------|
| Upload PDF natif `statuts.pdf` 2 MB | `ocr_status=done` | text_content non vide |
| Upload PDF scanné / JPG / .docx / .xlsx | `ocr_status=deferred` | text_content NULL |
| Upload .exe | 415 mime_not_allowed | rien persisté |
| Upload 30 MB | 413 size_too_large | rien persisté |
| 51e upload | 409 too_many_documents | |
| Upload sans entreprise | 400 entreprise_required | |
| Cross-tenant GET/DELETE | 404 not_found | |
