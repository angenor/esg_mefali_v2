# Contract — Memory Endpoint (`GET` / `DELETE /me/chat/threads/{id}/memory`)

## GET /me/chat/threads/{thread_id}/memory

Retourne le snapshot mémoire du thread (FR-007, US3). Backwards-compatible avec F18 (champs ajoutés, pas renommés).

### Request

```http
GET /me/chat/threads/{thread_id}/memory HTTP/1.1
Authorization: Bearer <jwt>
```

Auth required (PME ou Admin scope account).

### Response 200

```json
{
  "total_messages": 47,
  "recent_messages_count": 15,
  "summary": "Bullet points résumant les messages compactés ou null si aucune compaction.",
  "vector_index_size": 32,
  "last_compaction_at": "2026-05-04T12:34:56+00:00",
  "entities_referenced": [
    {"type": "Entreprise", "id": "5fcc1a...", "label": "ACME Boulangerie"},
    {"type": "Projet", "id": "8e2b3c...", "label": "Solaire 50 kWc"}
  ]
}
```

Pydantic schema : `MemorySnapshotV2` (cf. data-model.md §4.2). Validation stricte (`extra='forbid'`).

### Response 404 (cross-tenant ou thread inconnu, P2)

```json
{ "detail": "Thread not found" }
```

### Response 401

Auth manquante / invalide.

### Performance

- p95 < 100 ms (lecture DB + agg `entities_referenced` JSONB).
- Pas de cache (read-time fresh).

### Security / RLS

- `account_id` GUC SET via middleware F02.
- Query thread filtrée par `account_id = current_setting('app.current_account_id')::uuid`.
- Cross-tenant ⇒ 404 (P2).

### Test cases (Acceptance)

| ID | Given | When | Then |
|---|---|---|---|
| GET-001 | Thread 47 msgs, 32 indexed, compacté il y a 2j | GET memory | 200 + tous les champs remplis |
| GET-002 | Thread 5 msgs, jamais compacté | GET memory | 200 + summary=null + last_compaction_at=null |
| GET-003 | Thread account B, JWT account A | GET memory | 404 |
| GET-004 | Thread inexistant | GET memory | 404 |

## DELETE /me/chat/threads/{thread_id}/memory

Forget RGPD synchrone (FR-008, US4). Idempotent.

### Request

```http
DELETE /me/chat/threads/{thread_id}/memory HTTP/1.1
Authorization: Bearer <jwt>
```

### Response 200

```json
{
  "thread_id": "5fcc1a...",
  "embeddings_purged": 32,
  "summary_cleared": true,
  "last_compaction_cleared": true,
  "messages_kept_for_audit": 47,
  "agent_entity_memory_unchanged": true,
  "audit_log_id": "9b3e1f..."
}
```

### Response 404

Cross-tenant ou thread inconnu (P2).

### Effets DB

1. `UPDATE chat_message SET embedding = NULL WHERE thread_id = :id` (RLS-scoped).
2. `UPDATE chat_thread SET summary = NULL, last_compacted_at = NULL WHERE id = :id` (RLS-scoped).
3. `INSERT INTO audit_log` avec `entity_type='ChatThread'`, `entity_id=:id`, `action='memory_forget'`, `source_of_change='memory_system'`, `field='memory'`, `old_value=<jsonb summary count of embeddings>`, `new_value=null`.
4. **NE TOUCHE PAS** `chat_message.content` (P3 audit append-only).
5. **NE TOUCHE PAS** `agent_entity_memory` (faits account-wide, Clarification Q3).
6. **NE TOUCHE PAS** `recall_log` (historique tracing).

### Performance

- p95 < 500 ms (un seul UPDATE par table, pas de LLM call).
- Synchrone : la réponse 200 garantit que la purge est effectivement faite (NFR-006).

### Security / RLS

- Vérification d'existence du thread sous `account_id` GUC avant purge.
- Cross-tenant ⇒ 404.
- Audit log obligatoire (P3).

### Idempotence

Appel répété : 200 OK avec `embeddings_purged=0` la deuxième fois.

### Test cases (Acceptance)

| ID | Given | When | Then |
|---|---|---|---|
| DEL-001 | Thread 50 msgs, 32 indexed, compacté | DELETE memory | 200 + 32 embeddings NULL + summary NULL + 50 contents intacts + 1 ligne audit_log |
| DEL-002 | Thread vide | DELETE memory | 200 idempotent + 0 embeddings purgés |
| DEL-003 | Thread account B, JWT account A | DELETE memory | 404 + aucune mutation |
| DEL-004 | Thread + agent_entity_memory existante | DELETE memory | 200 + entity_memory inchangée |
| DEL-005 | Compaction en cours sur même thread | DELETE memory | attend lock (≤ 5 s), puis purge proprement |
