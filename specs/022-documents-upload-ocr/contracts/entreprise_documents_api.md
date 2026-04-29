# API Contract — `/me/entreprise/documents`

Tous les endpoints requièrent l'authentification PME (`get_current_pme`). Erreurs : `{code, message}` sous `detail`.

## POST `/me/entreprise/documents`

Multipart/form-data.

- `file` (UploadFile, required)
- `type` (str, required) ∈ `statuts | rapport_activite | facture | contrat | politique | autre`
- `name` (str, optional) — défaut = `file.filename`

**201 Created**:
```json
{
  "id": "uuid",
  "entreprise_id": "uuid",
  "name": "Statuts SARL.pdf",
  "original_filename": "statuts.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 124567,
  "type": "statuts",
  "ocr_status": "done",
  "ocr_error": null
}
```

Erreurs : `400 entreprise_required` · `409 too_many_documents` · `413 size_too_large` · `415 mime_not_allowed` · `422 doc_type_invalid`.

## GET `/me/entreprise/documents`

**200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "entreprise_id": "uuid",
      "name": "...",
      "original_filename": "...",
      "mime_type": "...",
      "size_bytes": 124567,
      "type": "statuts",
      "ocr_status": "done",
      "ocr_error": null,
      "uploaded_by": "uuid|null",
      "created_at": "2026-04-29T10:30:00"
    }
  ]
}
```

Erreurs : `400 entreprise_required`.

## GET `/me/entreprise/documents/{doc_id}`

**200**: payload identique aux items du listing.
**404 not_found** : inexistant ou cross-tenant.

## GET `/me/entreprise/documents/{doc_id}/download`

**200** : `Content-Type: <mime>`, `Content-Disposition: attachment; filename="<original_filename>"`, body bytes.
**404 not_found**.

Audit : `entity_type=document_entreprise, action=download`.

## DELETE `/me/entreprise/documents/{doc_id}`

Soft-delete + suppression best-effort du fichier.
**204 No Content** · **404 not_found** (idempotent).

## Codes d'erreur récapitulatif

| HTTP | Code | Cause |
|------|------|-------|
| 400 | entreprise_required | Pas d'entreprise associée |
| 404 | not_found | Document absent / cross-tenant / déjà supprimé |
| 409 | too_many_documents | Cap 50 atteint |
| 413 | size_too_large | > 25 MB |
| 415 | mime_not_allowed | Mime hors whitelist |
| 422 | doc_type_invalid | Type métier hors enum |

## Schémas Pydantic

```python
class DocumentOut(BaseModel):
    id: UUID
    entreprise_id: UUID
    name: str
    original_filename: str
    mime_type: str
    size_bytes: int
    type: str
    ocr_status: str
    ocr_error: str | None = None
    uploaded_by: UUID | None = None
    created_at: datetime | None = None

class DocumentListOut(BaseModel):
    items: list[DocumentOut]
```
