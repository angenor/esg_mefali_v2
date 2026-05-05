# API Contract — Extensions F50 sur `/me/documents` et `/me/entreprise/documents`

Tous les endpoints ci-dessous étendent l'API F22 existante. Ils requièrent l'authentification PME (`get_current_pme`). Erreurs sous `detail: {code, message}`. Cross-tenant → 404 (P2).

## 1. Pre-flight dédoublonnage par empreinte

### `GET /me/documents/by-fingerprint`

Query : `sha256` (hex 64 chars, requis).

**200 OK** — un document du même compte porte déjà cette empreinte (et n'est pas soft-deleted) :

```json
{
  "document": {
    "id": "uuid",
    "name": "Statuts SARL.pdf",
    "mime_type": "application/pdf",
    "size_bytes": 124567,
    "ocr_status": "done",
    "extraction_validated_at": "2026-04-30T15:00:00Z",
    "linked_projets": ["uuid", "uuid"]
  }
}
```

**404 Not Found** — aucun doublon ; le client peut procéder à l'upload normalement.

**400 invalid_fingerprint** — `sha256` non conforme (hex 64).

## 2. Upload (`POST /me/entreprise/documents`) — extensions

L'endpoint F22 existant reste compatible. Champs ajoutés :

- `client_sha256` (form, optionnel) : empreinte SHA-256 hex calculée côté client à des fins de cohérence (jamais utilisée seule pour la sécurité).
- `link_projet_id` (form, optionnel, UUID) : si fourni, le serveur crée AUSSI une entrée `document_link_projet` après création du document.

Réponse 201 (extension de la forme F22) :

```json
{
  "id": "uuid",
  "entreprise_id": "uuid",
  "name": "Statuts SARL.pdf",
  "original_filename": "statuts.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 124567,
  "type": "statuts",
  "ocr_status": "pending",
  "ocr_error": null,
  "content_sha256": "abc123…",
  "extraction_payload": {},
  "extraction_validated_at": null,
  "linked_projets": ["uuid"]
}
```

Codes d'erreur additionnels :

| HTTP | Code | Cause |
|------|------|-------|
| 409 | duplicate_fingerprint | Si le client envoie `force_new=false` dans le futur ; en MVP le serveur n'impose pas — c'est le client qui doit avoir résolu via le pre-flight. |
| 422 | projet_not_found | `link_projet_id` invalide ou cross-tenant. |

## 3. Lecture (statuts OCR & extraction)

### `GET /me/entreprise/documents/{id}`

Réponse étendue (champs ajoutés en gras) :

```json
{
  "id": "uuid",
  "entreprise_id": "uuid",
  "name": "...",
  "mime_type": "application/pdf",
  "size_bytes": 124567,
  "type": "statuts",
  "ocr_status": "done",
  "ocr_error": null,
  "uploaded_by": "uuid",
  "created_at": "2026-04-29T10:30:00Z",
  "content_sha256": "abc123…",
  "extraction_payload": {
    "fields": [
      { "key": "raison_sociale", "label": "Raison sociale", "value": "Acme SARL", "confidence": 0.94 },
      { "key": "effectifs", "label": "Effectifs", "value": 12, "confidence": 0.71 },
      { "key": "ca", "label": "Chiffre d'affaires", "value": { "amount": "12500000", "currency": "XOF" }, "confidence": 0.82 }
    ]
  },
  "extraction_validated_at": null,
  "extraction_validated_by": null,
  "linked_projets": ["uuid", "uuid"],
  "tags": ["Bilan 2024"],
  "deleted_at": null,
  "purge_scheduled_at": null
}
```

Codes : `404 not_found`.

## 4. Validation de l'extraction

### `POST /me/entreprise/documents/{id}/validate`

Body :

```json
{
  "fields": [
    { "key": "raison_sociale", "value": "Acme SARL" },
    { "key": "effectifs", "value": 18 },
    { "key": "ca", "value": { "amount": "12500000", "currency": "XOF" } }
  ],
  "propagate_to": [
    { "entity": "entreprise", "id": "uuid" },
    { "entity": "projet", "id": "uuid" }
  ]
}
```

Schéma Pydantic (extra='forbid', closed enums sur `entity`).

**200 OK** :

```json
{
  "id": "uuid",
  "extraction_validated_at": "2026-05-05T14:23:11Z",
  "extraction_validated_by": "uuid",
  "propagated": [
    { "entity": "entreprise", "id": "uuid", "fields_updated": ["raison_sociale", "effectifs", "ca"] },
    { "entity": "projet", "id": "uuid", "fields_updated": [] }
  ]
}
```

Codes :

| HTTP | Code | Cause |
|------|------|-------|
| 404 | not_found | Document inexistant ou cross-tenant |
| 409 | already_validated | Déjà validé — utiliser l'endpoint `/recorrect` (POST avec `invalidate_existing=true`) |
| 422 | invalid_field | Clé inconnue / type incompatible |
| 422 | invalid_propagation_target | Entité inconnue ou cross-tenant |

Audit : `validate_extraction` + per-field `update` sur les entités cibles.

### `POST /me/entreprise/documents/{id}/relaunch-ocr`

Body :

```json
{ "invalidate_existing_validation": true }
```

**202 Accepted** — le document repasse en `ocr_status='processing'` et `extraction_validated_at` redevient NULL si `invalidate_existing_validation=true`.

Codes : `404 not_found`, `409 ocr_in_progress` (si déjà en cours).

## 5. Liens projet (M:N — Q1)

### `POST /me/entreprise/documents/{id}/link-projet`

Body : `{ "projet_id": "uuid" }`

**201 Created** : crée la ligne `document_link_projet`. Idempotent : 200 OK si le lien existait déjà.

Codes : `404 not_found` (document/projet absent ou cross-tenant), `422 same_account_required`.

### `DELETE /me/entreprise/documents/{id}/link-projet/{projet_id}`

**204 No Content** (idempotent — 204 même si le lien n'existait pas).

### `GET /me/projets/{projet_id}/documents`

Union de :

- `document_projet` (legacy F12, lien direct).
- `document_entreprise` joint à `document_link_projet WHERE projet_id = $1`.

```json
{
  "items": [
    {
      "id": "uuid",
      "source": "document_entreprise",
      "name": "...",
      "mime_type": "...",
      "ocr_status": "done",
      "extraction_validated_at": "...",
      "tags": ["..."]
    },
    {
      "id": "uuid",
      "source": "document_projet",
      "name": "...",
      "mime_type": "...",
      "ocr_status": "done"
    }
  ]
}
```

## 6. Suppression et purge

### `DELETE /me/entreprise/documents/{id}` (extension F22)

Comportement F22 conservé + ajout : `purge_scheduled_at = deleted_at + interval '30 days'`. **204 No Content.**

### `POST /admin/documents/purge` (admin only)

Endpoint interne déclenché par cron OS / CI. Sélectionne `document_entreprise` avec `purge_scheduled_at <= now()` et exécute :

1. Suppression du fichier sur le storage.
2. Suppression des liens `document_link_projet` (CASCADE).
3. Suppression de la ligne `document_entreprise`.
4. `record_audit(action='hard_purge', source_of_change='system')`.

Réponse : `{ "purged": <count> }`.

## 7. Schémas Pydantic ajoutés (résumé)

```python
class ExtractedField(BaseModel):
    model_config = ConfigDict(extra='forbid')
    key: str
    label: str | None = None
    value: Any   # str | int | float | bool | dict (pour Money) — validé par dispatch
    confidence: float = Field(ge=0, le=1)

class ExtractionPayload(BaseModel):
    model_config = ConfigDict(extra='forbid')
    fields: list[ExtractedField] = []

class ValidateExtractionIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    fields: list[ExtractedFieldValue]
    propagate_to: list[PropagationTarget] = []

class PropagationTarget(BaseModel):
    model_config = ConfigDict(extra='forbid')
    entity: Literal['entreprise', 'projet']
    id: UUID

class FingerprintLookupOut(BaseModel):
    model_config = ConfigDict(extra='forbid')
    document: DocumentOut

class LinkProjetIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    projet_id: UUID
```

## 8. Erreurs récapitulatives F50

| HTTP | Code | Endpoint(s) |
|------|------|-------------|
| 400 | invalid_fingerprint | by-fingerprint |
| 404 | not_found | tous |
| 409 | already_validated | validate |
| 409 | ocr_in_progress | relaunch-ocr |
| 409 | duplicate_fingerprint | upload (réservé future itération) |
| 422 | invalid_field | validate |
| 422 | invalid_propagation_target | validate |
| 422 | projet_not_found | upload, link-projet |
| 422 | same_account_required | link-projet |
