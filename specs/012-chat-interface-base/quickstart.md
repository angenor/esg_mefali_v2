# Quickstart — F13 Chat Interface Base (backend manual run)

## Prereqs

- Postgres + pgvector running via `docker-compose up -d`.
- Backend `.venv` activated, deps installed.
- `alembic upgrade head` succeeded (includes 0011 F13 migration).
- `LLM_API_KEY` is optional — without it, the assistant emits a deterministic stub.

## End-to-end (curl + sse listener)

1. Login as PME (existing F02 flow); capture JWT in `$JWT`, set `$APP_URL` and `$TID` after step 2.

2. Create a thread:
   ```bash
   curl -sX POST $APP_URL/me/chat/threads \
     -H "Authorization: Bearer $JWT" -H "Content-Type: application/json" -d '{}'
   # response: { "id": "<thread_uuid>", "title": "Conversation du DD/MM/YYYY", "archived": false, ... }
   ```

3. Open the assistant SSE stream:
   ```bash
   curl -N -X POST $APP_URL/me/chat/threads/$TID/messages \
     -H "Authorization: Bearer $JWT" -H "Content-Type: application/json" \
     -d '{"content":"bonjour","context_json":{"page":"/"}}'
   # SSE events: text_delta ... message_done
   ```

4. List messages:
   ```bash
   curl -s $APP_URL/me/chat/threads/$TID/messages -H "Authorization: Bearer $JWT" | jq
   # { "messages": [ {role:"user",...}, {role:"assistant",...} ] }
   ```

5. Subscribe to `/me/events` (second terminal):
   ```bash
   curl -N $APP_URL/me/events -H "Authorization: Bearer $JWT"
   ```

6. Publish an entity update from a Python shell:
   ```python
   from app.chat.event_bus import event_bus
   await event_bus.publish(account_id, {"type":"entity_updated","entity_type":"entreprise","entity_id":"<uuid>"})
   ```
   The second terminal receives `event: entity_updated`. Another tenant's events MUST not reach it.

7. Archive the thread:
   ```bash
   curl -X DELETE $APP_URL/me/chat/threads/$TID -H "Authorization: Bearer $JWT"
   # 204
   ```

8. Try posting again — expect 409:
   ```bash
   curl -i -X POST $APP_URL/me/chat/threads/$TID/messages \
     -H "Authorization: Bearer $JWT" -H "Content-Type: application/json" \
     -d '{"content":"hi","context_json":{"page":"/"}}'
   # HTTP/1.1 409 Conflict {"detail":"thread_archived"}
   ```

## Negative tests

- Extra `context_json` field (e.g., `secret`) → 422.
- Content > 32 KB → 413 or 422.
- Cross-tenant `GET /me/chat/threads/{other_tenant_thread_id}/messages` → 404.

## Acceptance signals

- SC-001: `bonjour` round-trip < 3 s.
- SC-004: 100% of `chat_message` rows have non-null `context_json`.
- SC-006: `tests/chat/test_rls_isolation.py` — zero rows leak across tenants.
