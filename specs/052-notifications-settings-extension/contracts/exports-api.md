# Contract — Exports API

---

## `GET /me/exports`

Liste des exports historiques (RGPD JSON, rapports PDF, attestations PDF, dossiers PDF).

**Query params** :

- `type` : `string` (`export_type`) — répétable.
- `cursor`, `limit` : pagination keyset (cf. notifications).

**200 OK** :

```json
{
  "items": [
    {
      "id": "uuid",
      "type": "rgpd_full",
      "format": "json",
      "size_bytes": 24567890,
      "status": "ready",
      "created_at": "2026-05-04T10:00:00Z",
      "ready_at": "2026-05-04T10:00:42Z",
      "signed_url": "https://eu-storage.../exports/...",
      "signed_url_expires_at": "2026-05-11T10:00:42Z",
      "delivered_via": "inapp"
    }
  ],
  "next_cursor": null
}
```

`signed_url` = `null` si `status ≠ ready` ou si `signed_url_expires_at < now()`.

---

## `POST /me/exports`

Génère un nouvel export à la demande.

**Request body** :

```json
{ "type": "rgpd_full", "format": "json" }
```

**Combinaisons valides** :

| `type` | `format` |
|--------|----------|
| `rgpd_full` | `json` |
| `report_pdf` | `pdf` (un `report_id` requis) |
| `attestation_pdf` | `pdf` (un `attestation_id` requis) |
| `dossier_pdf` | `pdf` (un `candidature_id` requis) |

**202 Accepted** :

```json
{ "id": "uuid", "status": "pending", "created_at": "2026-05-05T12:00:00Z" }
```

Le client polle `GET /me/exports/{id}` ou écoute le SSE notifications (un event `notification.created` de kind `system` est émis quand `status=ready`).

---

## `GET /me/exports/{id}`

Détail d'un export. Si `size_bytes > 100 MB` au moment du `ready` → `delivered_via=email` (pas de `signed_url` retournée — l'utilisateur reçoit le lien par mail).

**200 OK** : payload item.
**404** : introuvable / cross-tenant.
**410 Gone** : `status=expired`.

---

## `GET /me/data/export` *(existant — F32)*

Conservé pour compat ; redirige désormais vers `POST /me/exports {type: "rgpd_full"}` côté frontend ; le endpoint backend reste pour scripts CLI.

---

## Validation Pydantic

```python
class ExportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: ExportType
    format: Literal["pdf", "json"]
    report_id: UUID | None = None
    attestation_id: UUID | None = None
    candidature_id: UUID | None = None

    @model_validator(mode="after")
    def _consistency(self) -> "ExportCreate":
        # forces les couples (type, format) listés ; rejette les ID croisés.
        ...


class ExportOut(BaseModel):
    id: UUID
    type: ExportType
    format: Literal["pdf", "json"]
    size_bytes: int | None
    status: ExportStatus
    created_at: datetime
    ready_at: datetime | None
    signed_url: HttpUrl | None
    signed_url_expires_at: datetime | None
    delivered_via: Literal["inapp", "email"] | None
```
