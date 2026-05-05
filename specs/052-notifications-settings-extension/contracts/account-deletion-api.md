# Contract — Account deletion + sessions API

---

## `GET /me/account-deletion`

État courant de la demande de suppression.

**200 OK** :

```json
{
  "request": {
    "id": "uuid",
    "status": "pending",
    "requested_at": "2026-05-05T12:00:00Z",
    "scheduled_for": "2026-06-04T12:00:00Z",
    "can_cancel": true
  }
}
```

Si aucune demande en cours : `{ "request": null }`.

---

## `POST /me/account-deletion`

Crée une demande. Saisie de la raison sociale exacte = preuve d'intention.

**Request body** :

```json
{
  "confirmation_text": "ACME SARL",
  "reason_motif": "string | null"
}
```

**Validation serveur** : `confirmation_text` doit matcher exactement `entreprise.raison_sociale` du compte (égalité après trim + collapse spaces). Si mismatch → 400 `confirmation_mismatch`.

**201 Created** : payload identique à `GET`.

**Effets** : audit log, e-mail de confirmation envoyé, notification in-app `system` créée.

**Erreurs** :

- 400 `confirmation_mismatch`
- 409 `already_pending` (une demande active existe déjà)

---

## `DELETE /me/account-deletion/{id}`

Annule une demande `pending`. Seul le user qui a initié peut annuler.

**204 No Content**. **404** si introuvable, **409** si statut ≠ `pending`.

---

## `GET /me/sessions`

Liste des sessions actives (non révoquées, non expirées).

**200 OK** :

```json
{
  "items": [
    {
      "id": "uuid",
      "device_label": "MacBook Pro — Safari 18",
      "ip_country": "CI",
      "user_agent_summary": "Safari/18.0 macOS",
      "created_at": "2026-05-01T08:00:00Z",
      "last_seen_at": "2026-05-05T11:32:00Z",
      "is_current": true
    }
  ]
}
```

---

## `DELETE /me/sessions/{id}`

Révoque une session. Si `id` correspond à la session courante → 400 `cannot_revoke_current` (utiliser `/auth/logout`).

**204 No Content**.

---

## `GET /me/consents`

*(existant — F05)* Réutilisé. F52 ajoute uniquement le bouton de retrait dans l'UI.

---

## `POST /me/consents/{id}/withdraw` *(existant)*

Audit log + e-mail de confirmation.

---

## Validation Pydantic

```python
class AccountDeletionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmation_text: str = Field(min_length=1, max_length=255)
    reason_motif: str | None = Field(default=None, max_length=1024)


class AccountDeletionOut(BaseModel):
    id: UUID
    status: Literal["pending", "cancelled", "executed"]
    requested_at: datetime
    scheduled_for: datetime
    can_cancel: bool
```
