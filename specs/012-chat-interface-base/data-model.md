# Phase 1 — Data Model: F13 Chat Interface Base

## Tables

### `chat_thread` (NEW)

| Column | Type | Constraint |
|---|---|---|
| `id` | UUID | PK, default `gen_random_uuid()` |
| `account_id` | UUID | NOT NULL, FK `account(id)` |
| `user_id` | UUID | NULL, FK `account_user(id)` |
| `title` | TEXT | NOT NULL |
| `archived` | BOOLEAN | NOT NULL, default `false` |
| `created_at` | TIMESTAMP | NOT NULL, default `now()` |
| `updated_at` | TIMESTAMP | NOT NULL, default `now()` |
| `version` | INT | NOT NULL, default 1 |
| `deleted_at` | TIMESTAMP | NULL |

**Indexes**: `ix_chat_thread_account_user` on `(account_id, user_id, archived, updated_at DESC)`.

**RLS**: enabled + forced; policy `USING (account_id = current_setting('app.current_account_id', true)::uuid)`.

### `chat_message` (ALTER)

Existing columns from F01: `id, account_id, user_id, role, content, payload_json, embedding vector(1024), version, deleted_at, created_at, updated_at`.

Add:

| Column | Type | Constraint |
|---|---|---|
| `thread_id` | UUID | NULL, FK `chat_thread(id)` ON DELETE CASCADE |
| `context_json` | JSONB | NULL |

Add CHECK constraint: `role IN ('user','assistant','system','tool')`.

**Indexes**: `ix_chat_message_thread_created` on `(thread_id, created_at)`.

**RLS**: already enabled in F01.

## Audit log entries

`audit_log` row appended with `source_of_change ∈ {'manual','llm'}` for:
- `chat_thread:create` (manual)
- `chat_thread:archive` (manual)
- `chat_message:insert:user` (manual)
- `chat_message:insert:assistant` (llm)

## Domain types (Pydantic v2)

```python
class ContextJson(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    selection: str | None = None

class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"   # never returned to client read endpoints
    tool = "tool"

class SsEvent(BaseModel):
    type: Literal["text_delta","tool_call_started","tool_call_completed","message_done","error"]
    data: dict[str, Any]
```

## State transitions

`chat_thread.archived`: false → true (one-way for F13). Unarchive OUT OF SCOPE.

## Validation rules

- `content` length ≤ 32 KB.
- `payload_json` serialized length ≤ 64 KB.
- Total request body ≤ 128 KB (middleware) → 413.
- `context_json` extra/unknown fields → 422.
- `POST messages` on archived thread → 409 `thread_archived`.
- Inserted `chat_message.thread_id` MUST resolve to a thread within caller's `account_id` (server-enforced + RLS).
