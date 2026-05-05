# Contrats API consommés (référence — non créés par F41)

F41 est une couche frontend pure. Elle **consomme** les endpoints suivants déjà publiés par F12 (chat) et F18 (memory + events). Toute évolution de ces contrats relève des features propriétaires.

## F12 — Chat

### `GET /me/chat/threads`

Liste les threads du compte courant.

**Réponse 200** :
```json
{
  "threads": [
    {
      "id": "uuid",
      "title": "string",
      "last_message_at": "ISO-8601 | null",
      "created_at": "ISO-8601",
      "archived": false
    }
  ]
}
```

### `POST /me/chat/threads`

Crée un thread vide (titre auto par défaut).

**Body** : `{ title?: string }`

**Réponse 201** : `{ id, title, last_message_at, created_at, archived }`

### `DELETE /me/chat/threads/{thread_id}` → 204

### `GET /me/chat/threads/{thread_id}/messages?limit=200`

**Réponse 200** :
```json
{
  "messages": [
    {
      "id": "uuid",
      "thread_id": "uuid",
      "role": "user | assistant | system",
      "content": "string",
      "payload_json": {},
      "sequence_id": 0,
      "created_at": "ISO-8601"
    }
  ]
}
```

### `POST /me/chat/threads/{thread_id}/messages`

Persiste le message utilisateur **et** retourne le stream SSE de la réponse assistant. Cible `media_type: text/event-stream`.

**Body** :
```json
{
  "content": "string (≤ 32000)",
  "payload_json": { "kind": "...", ... } | null,
  "context_json": { "force_freetext": true } | null
}
```

**Réponse SSE — frames émises** :

| event | data (JSON) | description |
|-------|-------------|-------------|
| `message_started` | `{ message_id, thread_id }` | bulle assistant ouverte |
| `token` | `{ id, delta, sequence_id }` | fragment Markdown |
| `tool_invoke` | `{ tool, args }` | F14 demande un bottom sheet ou une viz |
| `mutation` | `{ entity_type, entity_id, fields_updated, source: "llm" }` | mutation propagée (F17) |
| `message_done` | `{ message_id, sequence_id_max }` | bulle finalisée |
| `error` | `{ code, message }` | échec validation/timeout/réseau |

**Erreurs HTTP** : `404 thread_not_found`, `409 thread_archived`, `422` payload invalide.

## F18 — Memory & events

### `GET /me/chat/threads/{thread_id}/memory`

**Réponse 200** :
```json
{
  "thread_id": "uuid",
  "size": 0,
  "entries": [{ "kind": "...", "preview": "...", "entity_ref": "..." }]
}
```

### `GET /me/events` (SSE)

Flux d'événements globaux du compte (un par onglet).

**Frames émises** :

| event | data |
|-------|------|
| `entity_updated` | `{ entity_type, entity_id, fields_updated, source }` |
| `entity_created` | idem |
| `entity_deleted` | `{ entity_type, entity_id, source }` |
| `memory_updated` | `{ thread_id, size }` |

`source ∈ { llm, manual, import, admin }` — le client F41 filtre `source === 'llm'` quand un listener déclencherait à nouveau le LLM (anti-loop P8).

## Sécurité — contrat partagé

- Auth : cookie de session PME (déjà géré par `useAuth`).
- CSRF : header `x-csrf-token` automatiquement injecté par le plugin `useCsrf` (déjà en place).
- CORS : allow-list backend.
- Sanitize : tout `content` côté client passe par DOMPurify avant rendu (cf. `research.md` R2).
