# Contract — Extension messaging & sidepanel API

Surface : interactions entre `content.js` ↔ `background.js` ↔ backend FastAPI ↔ `sidepanel/App.vue`.

---

## REST — endpoints backend dédiés

### `POST /me/extension/ping`

Heartbeat émis par le service worker au démarrage et toutes les 30 minutes.

**Request body** :

```json
{ "extension_version": "0.4.2", "user_agent_summary": "Chrome/124.0 macOS" }
```

**204 No Content**. UPSERT idempotent sur `(user_id)`.

---

### `GET /me/extension/status`

Consommé par `/parametres` (US9 / FR-028).

**200 OK** :

```json
{
  "detected": true,
  "extension_version": "0.4.2",
  "last_ping_at": "2026-05-05T11:48:00Z"
}
```

`detected=false` si pas de ping ou `last_ping_at < now() - 24 h`.

---

### `GET /me/extension/sidepanel-context`

Endpoint unique consommé par le sidepanel à chaque ouverture. Le `url_pattern` matché est passé en query param pour scope du contexte.

**Query params** :

- `host` : `string` — domaine de l'onglet courant.
- `path` : `string` — chemin de l'URL.

**200 OK** :

```json
{
  "matched_offer_ids": ["uuid", "uuid"],
  "active_candidatures": [
    {
      "id": "uuid",
      "offer_label": "BOAD — Ligne verte 2026",
      "deadline_at": "2026-06-01T23:59:00Z",
      "completion_pct": 62,
      "resume_url": "https://app.../candidatures/<uuid>"
    }
  ],
  "recommended_offers": [
    {
      "id": "uuid",
      "label": "AFD — Climat & Genre",
      "match_score": 0.81,
      "matching_url": "https://app.../matching?offer=<uuid>"
    }
  ]
}
```

Si l'host/path ne matche aucun pattern actif (vérifié serveur) : 200 avec listes vides.

**Erreurs** : 401 si non authentifié → le sidepanel affiche l'état "Veuillez vous connecter" + lien vers la plateforme.

---

## Messages `chrome.runtime`

| Direction | Type | Payload | But |
|-----------|------|---------|-----|
| `content` → `background` | `URL_DETECTED` | `{ host, path, pattern_id }` | déclencher l'ouverture du sidepanel |
| `content` → `background` | `PANEL_DISMISS` | `{}` | fermer le panneau pour la session de l'onglet |
| `background` → `sidepanel` | `CONTEXT_READY` | `SidepanelContextOut` | injecter le contexte fetché |
| `sidepanel` → `background` | `OPEN_CANDIDATURE` | `{ id }` | ouvre `resume_url` dans un nouvel onglet |
| `sidepanel` → `background` | `OPEN_MATCHING` | `{ offer_id }` | ouvre `matching_url` dans un nouvel onglet |
| `background` → `sidepanel` | `AUTH_REQUIRED` | `{ login_url }` | demande à l'utilisateur de se connecter à l'app |

**Règles** :

- Aucun message **ne véhicule** de payload tenant en provenance du `content` script (cf. R7) — les contextes sensibles sont **toujours** fetchés depuis le `background` via `credentials: 'include'`.
- Le `background` valide `sender.tab.url` contre le catalogue d'URL patterns avant tout fetch.
- Les messages ignorent les expéditeurs sans `sender.tab` (filtrage iframe / page non onglet).

---

## Validation Pydantic (backend)

```python
class ExtensionPingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    extension_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    user_agent_summary: str = Field(max_length=255)


class SidepanelCandidatureItem(BaseModel):
    id: UUID
    offer_label: str
    deadline_at: datetime
    completion_pct: int = Field(ge=0, le=100)
    resume_url: HttpUrl


class SidepanelContextOut(BaseModel):
    matched_offer_ids: list[UUID]
    active_candidatures: list[SidepanelCandidatureItem]
    recommended_offers: list[SidepanelOfferItem]
```

---

## Notifications push de l'extension (P2)

`chrome.notifications.create` est invoqué par le service worker uniquement si :

- L'utilisateur a accepté la permission OS.
- Une notification serveur de kind `deadline_j_minus_1` est reçue (le service worker écoute le SSE backend `/me/notifications/stream` via `EventSource` proxy déclenché à l'ouverture du popup ou périodiquement).

Le clic appelle `chrome.tabs.create({ url: notification.link })`. Pas de payload tenant stocké côté `chrome.storage`.
