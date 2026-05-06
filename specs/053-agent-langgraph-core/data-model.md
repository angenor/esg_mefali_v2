# Phase 1 — Data Model : F53 Agent LangGraph Core

**Branch** : `053-agent-langgraph-core`
**Date** : 2026-05-06

## 1. AgentState (in-memory + checkpointed)

Pydantic v2 `BaseModel` with `model_config = ConfigDict(extra='forbid', arbitrary_types_allowed=True)`. Type définis dans `backend/app/agent/state.py`.

### 1.1 Champs

| Champ | Type | Default | Notes |
|-------|------|---------|-------|
| `thread_id` | `str` (composite `{account_id_uuid}:{conv_uuid}`) | required | Validé par regex pattern ; isolation tenant (Q2 clarification) |
| `account_id` | `UUID` | required | Identité tenant ; injecté par middleware auth |
| `user_id` | `UUID` | required | Utilisateur courant ; injecté par middleware auth |
| `user_message` | `str` | required | Message utilisateur entrant (non vide, max 4000 chars) |
| `context_json` | `ContextJson` | required | Contexte de page (`page_route`, `entity_id`, `mode`) — provenant de F13 |
| `intent` | `Intent | None` | None | Classifié par nœud `route` |
| `system_prompt` | `str` | `""` | Alimenté par F54 ; F53 expose le hook |
| `messages` | `list[BaseMessage]` (LangChain) | `[]` | Historique LangChain ; reducer = `add_messages` |
| `available_tools` | `list[ToolDef]` | `[]` | Sous-ensemble retenu pour ce tour (≤ 10) |
| `llm_response` | `AIMessage | None` | None | Réponse LLM courante (avant validation) |
| `tool_calls` | `list[ToolCall]` | `[]` | Tool calls bruts extraits du LLM |
| `validated_calls` | `list[ValidatedToolCall]` | `[]` | Tool calls passés Pydantic strict |
| `dispatch_results` | `list[ToolDispatchResult]` | `[]` | Résultats du dispatch (DB / SSE / re-call) |
| `final_text` | `str` | `""` | Texte assistant final |
| `retry_count` | `int` | `0` | Compteur retry validate ; max = `LLM_AGENT_MAX_RETRIES` |
| `errors` | `list[AgentError]` | `[]` | Erreurs accumulées |

### 1.2 Types associés

```python
class Intent(StrEnum):
    PROFILAGE = "profilage"
    MUTATION = "mutation"
    ANALYSE = "analyse"
    AIDE = "aide"
    NAVIGATION = "navigation"
    AUTRE = "autre"
    QUESTION_FERMEE = "question_fermee"

class ContextJson(BaseModel):
    model_config = ConfigDict(extra='forbid')
    page_route: str                 # ex: "/profil/projets"
    entity_id: UUID | None = None
    mode: Literal["read", "edit"] = "read"
    locale: Literal["fr", "en"] = "fr"

class ToolCall(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str                         # tool_call_id LLM
    name: str                       # tool name
    arguments: dict[str, Any]       # raw arguments (JSON-serializable)

class ValidatedToolCall(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    name: str
    arguments: BaseModel            # validated Pydantic args (per tool schema)
    schema_version: str             # for audit

class DispatchCategory(StrEnum):
    SSE_ONLY = "sse_only"           # ask_*, show_*
    DB_MUTATION = "db_mutation"     # update_*, create_*, delete_*
    REINVOKE_LLM = "reinvoke_llm"   # cite_source, search_source, recall_history

class ToolDispatchResult(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tool_call_id: str
    tool_name: str
    category: DispatchCategory
    status: Literal["ok", "error", "skipped"]
    output: dict[str, Any] | None = None  # for REINVOKE_LLM, sent back to LLM
    error_summary: str | None = None
    db_audit_id: UUID | None = None       # if DB_MUTATION

class AgentError(BaseModel):
    model_config = ConfigDict(extra='forbid')
    node_name: str
    code: Literal[
        "validation_error",
        "dispatch_error",
        "llm_error",
        "timeout",
        "cancelled",
        "internal",
    ]
    message: str
    details: dict[str, Any] | None = None
    retriable: bool = False
```

### 1.3 Reducers (LangGraph annotations)

```python
class AgentState(BaseModel):
    model_config = ConfigDict(extra='forbid', arbitrary_types_allowed=True)
    # ... fields ...

    # LangGraph reducers (via Annotated)
    messages: Annotated[list[BaseMessage], add_messages]
    tool_calls: Annotated[list[ToolCall], _append]      # custom: extend list
    validated_calls: Annotated[list[ValidatedToolCall], _append]
    dispatch_results: Annotated[list[ToolDispatchResult], _append]
    errors: Annotated[list[AgentError], _append]
    # autres fields = clobber simple (default LangGraph)
```

## 2. AgentRun (table SQL append-only)

```sql
CREATE TYPE agent_run_status AS ENUM ('ok', 'error', 'timeout', 'cancelled');

CREATE TABLE agent_run (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id       UUID NOT NULL REFERENCES accounts(id),
    user_id          UUID NOT NULL REFERENCES users(id),
    thread_id        VARCHAR(128) NOT NULL,
    started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at     TIMESTAMPTZ NULL,
    status           agent_run_status NOT NULL DEFAULT 'ok',
    total_latency_ms INT NULL,
    total_tokens_in  INT NULL,
    total_tokens_out INT NULL,
    retry_count      INT NOT NULL DEFAULT 0,
    final_node       VARCHAR(64) NULL,
    error_summary    TEXT NULL,
    CONSTRAINT agent_run_thread_id_format CHECK (thread_id ~ '^[0-9a-f-]{36}:[0-9a-f-]{36}$')
);
CREATE INDEX idx_agent_run_account_thread ON agent_run(account_id, thread_id, started_at DESC);
CREATE INDEX idx_agent_run_status_started ON agent_run(status, started_at DESC) WHERE status != 'ok';

ALTER TABLE agent_run ENABLE ROW LEVEL SECURITY;
CREATE POLICY agent_run_account_isolation ON agent_run
    USING (account_id = current_setting('app.current_account_id')::uuid);

REVOKE UPDATE, DELETE ON agent_run FROM app_user;
```

### Ajout de colonnes : néant (table nouvelle, append-only).

### Lifecycle

- `INSERT` au début de `run_agent` avec `status='ok'`, `completed_at=NULL`.
- `INSERT` d'un nouveau row à la fin avec status final ? **Non** — on viole append-only en doublonnant. **Décision** : exception au strict append-only ; on autorise UNIQUEMENT le `UPDATE` du `completed_at`, `status`, `total_*`, `retry_count`, `final_node`, `error_summary` au sortir du run, **uniquement par le rôle `app_admin`**. L'`app_user` rôle n'a que `INSERT`. Le runner exécute le `UPDATE` final dans une session avec rôle élevé via `SET LOCAL ROLE app_admin` puis `RESET ROLE`.
- **Alternative considérée** : table `agent_run_completion` séparée — rejetée car overkill pour 1 row de complétion par run.
- Cette exception est documentée dans `backend/alembic/README.md` et le test `test_agent_run_append_only` vérifie qu'un INSERT d'un duplicate row est refusé et qu'un UPDATE non-app_admin est rejeté.

## 3. AgentRunStep (table SQL append-only)

```sql
CREATE TYPE agent_step_status AS ENUM ('ok', 'error', 'timeout', 'cancelled', 'skipped');

CREATE TABLE agent_run_step (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id           UUID NOT NULL REFERENCES agent_run(id) ON DELETE RESTRICT,
    account_id       UUID NOT NULL REFERENCES accounts(id),
    node_name        VARCHAR(64) NOT NULL,
    started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    latency_ms       INT NULL,
    tokens_in        INT NULL,
    tokens_out       INT NULL,
    tool_calls_count INT NOT NULL DEFAULT 0,
    status           agent_step_status NOT NULL DEFAULT 'ok',
    error            TEXT NULL
);
CREATE INDEX idx_agent_run_step_run ON agent_run_step(run_id, started_at);
CREATE INDEX idx_agent_run_step_account_node ON agent_run_step(account_id, node_name, started_at DESC);

ALTER TABLE agent_run_step ENABLE ROW LEVEL SECURITY;
CREATE POLICY agent_run_step_account_isolation ON agent_run_step
    USING (account_id = current_setting('app.current_account_id')::uuid);

REVOKE UPDATE, DELETE ON agent_run_step FROM app_user;
```

### Lifecycle

- 1 INSERT par exécution de nœud (à la fin du nœud, avec metrics complètes).
- Pas d'UPDATE — toutes les valeurs sont connues au sortir du nœud.
- ON DELETE RESTRICT empêche la suppression du `agent_run` parent (cohérence référentielle préservée).

## 4. Thread ID composite (Q2 clarification)

### Format

```
{account_uuid}:{conv_uuid}
```

Exemple : `5bc4d3a2-1234-5678-9abc-def012345678:7e8f9a0b-cdef-1234-5678-9abcdef01234`

### Construction

- Lors de la création d'un thread (frontend ou première requête), le runner reçoit `account_id` (de la session auth) et un `conv_uuid` v4 généré côté front (ou serveur si absent).
- Le runner construit `thread_id = f"{account_id}:{conv_uuid}"`.

### Validation

- Regex CHECK constraint sur `agent_run.thread_id` : `^[0-9a-f-]{36}:[0-9a-f-]{36}$`.
- Au runtime, `runner.run_agent` valide que le préfixe correspond à `account_id` de la session avant d'invoquer le checkpointer. Si mismatch → `ValueError("thread_id account prefix mismatch")` → 404 retourné au client (FR-013).

### Cas d'erreur

- Format invalide → 400 Bad Request (rejeté par le validator FastAPI).
- Préfixe différent de l'`account_id` session → 404 (silencieux, pas d'indice) — invariant P2.

## 5. AgentCheckpoint (gérée par LangGraph)

Table créée par `AsyncPostgresSaver.setup()`. Schéma exact dépend de `langgraph-checkpoint-postgres 2.0.x` ; à la date du plan :

```sql
-- créé automatiquement par .setup()
CREATE TABLE checkpoints (
    thread_id      TEXT NOT NULL,
    checkpoint_ns  TEXT NOT NULL,
    checkpoint_id  TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type           TEXT,
    checkpoint     JSONB,
    metadata       JSONB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
CREATE TABLE checkpoint_blobs (...);
CREATE TABLE checkpoint_writes (...);
```

**Important** :
- Pas de migration Alembic pour ces tables (Q1 clarification).
- Pas de RLS native — l'isolation est garantie par le `thread_id` composite (Q2 clarification).
- Documentation à ajouter dans `backend/alembic/README.md` :
  > Les tables `checkpoints*` sont gérées par `langgraph-checkpoint-postgres` via `AsyncPostgresSaver.setup()` au boot. Elles ne doivent **jamais** être versionnées par Alembic. L'isolation tenant est assurée par le préfixe `account_id` du `thread_id` composite (cf. `backend/app/agent/checkpointer.py`).

## 6. Migration Alembic

Une seule migration ajoutée par F53 : `backend/alembic/versions/0XXX_agent_run_steps.py`.

Contenu :

```python
"""f53 agent_run + agent_run_step

Revision ID: <auto>
Revises: <previous>
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa

revision = "<auto>"
down_revision = "<previous>"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # ENUMs
    op.execute("CREATE TYPE agent_run_status AS ENUM ('ok', 'error', 'timeout', 'cancelled')")
    op.execute("CREATE TYPE agent_step_status AS ENUM ('ok', 'error', 'timeout', 'cancelled', 'skipped')")

    # agent_run
    op.create_table(
        "agent_run",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("account_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("thread_id", sa.String(128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Enum("ok", "error", "timeout", "cancelled", name="agent_run_status"), nullable=False, server_default="ok"),
        sa.Column("total_latency_ms", sa.Integer(), nullable=True),
        sa.Column("total_tokens_in", sa.Integer(), nullable=True),
        sa.Column("total_tokens_out", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("final_node", sa.String(64), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.CheckConstraint(r"thread_id ~ '^[0-9a-f-]{36}:[0-9a-f-]{36}$'", name="agent_run_thread_id_format"),
    )
    op.create_index("idx_agent_run_account_thread", "agent_run", ["account_id", "thread_id", sa.text("started_at DESC")])
    op.create_index("idx_agent_run_status_started", "agent_run", ["status", sa.text("started_at DESC")], postgresql_where=sa.text("status != 'ok'"))

    # agent_run_step
    op.create_table(
        "agent_run_step",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_run.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("account_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("node_name", sa.String(64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("tool_calls_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.Enum("ok", "error", "timeout", "cancelled", "skipped", name="agent_step_status"), nullable=False, server_default="ok"),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("idx_agent_run_step_run", "agent_run_step", ["run_id", "started_at"])
    op.create_index("idx_agent_run_step_account_node", "agent_run_step", ["account_id", "node_name", sa.text("started_at DESC")])

    # RLS policies
    op.execute("ALTER TABLE agent_run ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE agent_run_step ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY agent_run_account_isolation ON agent_run USING (account_id = current_setting('app.current_account_id')::uuid)")
    op.execute("CREATE POLICY agent_run_step_account_isolation ON agent_run_step USING (account_id = current_setting('app.current_account_id')::uuid)")

    # Append-only (revoke for app_user, allow UPDATE for app_admin via runner SET LOCAL ROLE)
    op.execute("REVOKE UPDATE, DELETE ON agent_run FROM app_user")
    op.execute("REVOKE UPDATE, DELETE ON agent_run_step FROM app_user")

def downgrade() -> None:
    op.drop_table("agent_run_step")
    op.drop_table("agent_run")
    op.execute("DROP TYPE agent_step_status")
    op.execute("DROP TYPE agent_run_status")
```

## 7. Diagramme entité-relation

```
+----------------+        +-----------------+
|  agent_run     |  1    n|  agent_run_step |
|----------------|--------|-----------------|
| id (PK)        |        | id (PK)         |
| account_id (FK)|        | run_id (FK)     |
| user_id (FK)   |        | account_id (FK) |
| thread_id      |        | node_name       |
| started_at     |        | latency_ms      |
| completed_at   |        | tokens_in/out   |
| status         |        | tool_calls_cnt  |
| total_latency  |        | status          |
| total_tokens   |        | error           |
| retry_count    |        +-----------------+
| final_node     |
| error_summary  |
+----------------+
```

Pas de relation directe avec `chat_message`, `chat_thread`, `audit_log` au niveau SQL — la corrélation se fait via `thread_id` (string) et `tool_call_log` (référence par run_id si nécessaire post-MVP).

## 8. Validation FR-002 (AgentState extra='forbid')

Test unitaire :

```python
def test_agent_state_extra_forbid():
    with pytest.raises(ValidationError):
        AgentState(
            thread_id="...",
            account_id=...,
            user_id=...,
            user_message="...",
            context_json=...,
            unknown_field="hack",  # extra='forbid' must reject
        )
```

## 9. Couverture data-model

| Champ spec | Couvert par |
|-----------|-------------|
| FR-002 AgentState | Section 1 |
| FR-009 agent_run | Section 2 |
| FR-010 agent_run_step | Section 3 |
| FR-008 checkpoints | Section 5 |
| FR-013 thread_id composite | Section 4 |
| FR-011 RLS | Sections 2 et 3 (RLS policies) |
| Append-only P3 | Sections 2 et 3 (REVOKE) |
