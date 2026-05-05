# Contract — Notifications API (extensions F52)

Base : tous les endpoints requièrent cookie de session valide ; `account_id` injecté côté middleware (P2). Erreurs : 401 si non authentifié, 404 si ressource d'un autre tenant (P2 — pas de 403).

---

## `GET /me/notifications`

*(existant — référence pour F52)*

**Query params** :

- `unread_only` : `boolean` — défaut `false`.
- `kind` : `string` (`notification_kind`) — répétable, OR logique.
- `from`, `to` : `date-time` ISO 8601 — borne inclusive sur `created_at`.
- `cursor` : `string` opaque — pagination keyset.
- `limit` : `integer` 1..100, défaut 20.

**200 OK** :

```json
{
  "items": [
    {
      "id": "uuid",
      "kind": "deadline_j_minus_7",
      "title": "Candidature BOAD échoit dans 7 jours",
      "body": "string",
      "link": "/candidatures/<uuid>",
      "created_at": "2026-05-05T12:00:00Z",
      "read_at": null
    }
  ],
  "next_cursor": "string | null",
  "unread_count": 5
}
```

---

## `PATCH /me/notifications/{id}/read`

*(existant)*

**204 No Content** — idempotent.

---

## `POST /me/notifications/read-all` *(nouveau — F52)*

Marque comme lues toutes les notifications non-lues du user (filtre optionnel par `kind[]`).

**Request body** :

```json
{ "kinds": ["deadline_j_minus_7", "candidature_inactive"] }
```

`kinds` optionnel ; absent → toutes les non-lues.

**200 OK** :

```json
{ "updated_count": 12, "unread_count_after": 0 }
```

**Erreurs** : 400 si `kinds` contient une valeur hors enum.

---

## `GET /me/notifications/stream` *(SSE existant — F38)*

Pas de changement F52. Le composable front `useNotificationsStream` consomme :

- event `notification.created` → push en tête de liste.
- event `notification.read` → mute le row par `id`.
- event `notification.bulk_read` → ajouté F52, payload `{kind?, count}` pour synchroniser plusieurs onglets.

---

## Validation Pydantic (backend)

```python
class NotificationListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    unread_only: bool = False
    kind: list[NotificationKind] = Field(default_factory=list)
    from_: datetime | None = Field(default=None, alias="from")
    to: datetime | None = None
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class ReadAllRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kinds: list[NotificationKind] | None = None


class ReadAllResponse(BaseModel):
    updated_count: int
    unread_count_after: int
```
