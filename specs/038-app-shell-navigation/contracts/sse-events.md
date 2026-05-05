# Contract — SSE `/me/events` (F38 stub, F41 complet)

Endpoint Server-Sent Events permettant au shell d'être notifié en temps réel
des événements utilisateur. **F38 livre uniquement un stub keepalive** ; la
spécification complète des événements métier sera implémentée par F41.

## Endpoint

| Méthode | Chemin | Auth | Réponse |
|---|---|---|---|
| `GET` | `/me/events` | session valide (cookie httpOnly) | `text/event-stream`, chunked, sans timeout serveur explicite |

## Headers

**Requête** (envoyés automatiquement par `EventSource`) :

```
Accept: text/event-stream
Cache-Control: no-cache
```

**Réponse** :

```
Content-Type: text/event-stream
Cache-Control: no-cache, no-transform
X-Accel-Buffering: no
Connection: keep-alive
```

## Sécurité

- Auth via cookie de session (le middleware FastAPI applique `get_current_user`).
- Réponse 401 si la session est invalide ou absente.
- RLS : `app.current_account_id` est positionné par le middleware standard avant l'ouverture du flux. Aucun accès cross-tenant possible.
- Aucun token dans l'URL.

## Format des messages

### F38 — stub

Un seul type d'événement :

```
event: ping
data: 2026-05-03T10:00:00Z

```

- Émis toutes les 30 secondes.
- Le client (`EventSource`) ignore ces événements (pas de handler côté F38).
- Garantit la santé de la connexion et empêche les proxies de couper le flux.

### F41 — extension future (non livrée par F38)

Événements métier prévus, format JSON dans `data` :

```
event: notification.created
data: {"id":"01HXXX...","kind":"candidature","title":"...","body":"...","link":"/candidatures/abc","created_at":"2026-05-03T10:00:00Z"}

event: notification.read
data: {"id":"01HXXX..."}
```

Le shell F38 :
- s'abonne à `notification.created` → appelle `useNotificationsStore.pushFromStream(payload)`.
- ignore `notification.read` (sera utilisé par F41 pour synchroniser deux onglets).
- ignore tout autre `event:` non répertorié (forward-compatible).

## Comportement client (F38)

1. À l'ouverture du layout `default`, ouvrir `new EventSource('/me/events', { withCredentials: true })`.
2. À l'erreur (`onerror`) : fermer la connexion, démarrer un polling `setInterval` toutes les 60 s qui appelle `GET /me/notifications`.
3. Tenter une reconnexion SSE avec backoff exponentiel : 1 s, 2 s, 4 s, 8 s, plafond 30 s.
4. À la fermeture du layout (`onBeforeUnmount`) ou au `logout()` : fermer la connexion + clear l'interval.

## Comportement serveur (stub F38)

```python
# backend/app/notifications/stream.py (extrait conceptuel)
from sse_starlette.sse import EventSourceResponse
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/me", tags=["notifications-stream"])

@router.get("/events")
async def stream(user = Depends(get_current_user)):
    async def gen():
        while True:
            yield {"event": "ping", "data": datetime.utcnow().isoformat() + "Z"}
            await asyncio.sleep(30)
    return EventSourceResponse(gen())
```

## Tests d'acceptation

- **T-SSE-001** : `GET /me/events` sans cookie → 401.
- **T-SSE-002** : `GET /me/events` avec cookie valide → 200, `Content-Type: text/event-stream`, premier `:ping` ou `event: ping` reçu en < 35 s.
- **T-SSE-003** : la connexion reste ouverte > 60 s sans erreur (smoke test).
- **T-SSE-004** : déconnexion client (close TCP) ne provoque pas de fuite serveur (vérifié via une exécution back avec `CTRL+C`).

## Hors-scope F38

- Émission d'événements métier (`notification.created`, etc.) → F41.
- Persistance / replay d'événements manqués → F41.
- Heartbeat applicatif côté client (PING/PONG explicite) → couvert par le keepalive serveur, pas nécessaire au MVP.
