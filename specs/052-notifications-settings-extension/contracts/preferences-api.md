# Contract — Préférences (profil + notifications + e-mail) API

---

## `GET /me/notification-preferences`

Retourne la matrice complète (kind × channel). Auto-instancie les rows manquants à `enabled=true`.

**200 OK** :

```json
{
  "items": [
    { "kind": "deadline_j_minus_30", "channel": "email", "enabled": true },
    { "kind": "deadline_j_minus_30", "channel": "in_app", "enabled": true },
    { "kind": "deadline_j_minus_7",  "channel": "email", "enabled": true },
    { "kind": "deadline_j_minus_7",  "channel": "in_app", "enabled": true },
    { "kind": "deadline_j_minus_1",  "channel": "email", "enabled": true },
    { "kind": "deadline_j_minus_1",  "channel": "in_app", "enabled": true },
    { "kind": "candidature_inactive","channel": "email", "enabled": true },
    { "kind": "candidature_inactive","channel": "in_app", "enabled": true },
    { "kind": "offre_recommandee",   "channel": "email", "enabled": true },
    { "kind": "offre_recommandee",   "channel": "in_app", "enabled": true }
  ]
}
```

---

## `PATCH /me/notification-preferences`

Batch de mises à jour. Atomique (transaction unique).

**Request body** :

```json
{
  "updates": [
    { "kind": "deadline_j_minus_30", "channel": "email", "enabled": false },
    { "kind": "offre_recommandee",   "channel": "email", "enabled": false }
  ]
}
```

**200 OK** : payload identique à `GET`.

**Erreurs** : 400 si `kind`/`channel` hors enum, 422 si `updates` vide.

---

## `POST /me/email-change`

Demande de changement d'adresse e-mail. L'ancienne reste active jusqu'à validation.

**Request body** :

```json
{ "new_email": "user@example.com", "current_password": "string" }
```

**202 Accepted** :

```json
{ "email_pending": "user@example.com", "verification_sent_at": "2026-05-05T12:00:00Z" }
```

**Erreurs** : 401 si mot de passe incorrect, 409 si l'adresse est déjà utilisée par un autre compte.

---

## `POST /me/email-change/verify?token={token}`

Valide le token reçu par e-mail ; bascule `email_pending → email`. Audit log.

**200 OK** : `{ "email": "user@example.com" }`. **400** si token invalide/expiré.

---

## `POST /me/password-change`

Endpoint existant (F02/F42). Référencé depuis `/parametres/profil`.

---

## `GET /me/preferences` *(existant — onboarding state)*

Étendu **non bloquant** côté F52 : la page `/parametres/profil` consomme `language` et `name` depuis `account_user`, pas depuis `user_preferences`.

---

## Validation Pydantic

```python
class NotificationPreferenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: NotificationKind
    channel: Literal["email", "in_app"]
    enabled: bool


class NotificationPreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    updates: list[NotificationPreferenceItem] = Field(min_length=1, max_length=50)


class EmailChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_email: EmailStr
    current_password: SecretStr
```
