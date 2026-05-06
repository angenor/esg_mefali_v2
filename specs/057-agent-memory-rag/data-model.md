# Phase 1 — Data Model (F57 Agent Memory & RAG)

## 1. Tables modifiées

### 1.1 `chat_thread`

Existant (F12/F18) ; F57 ajoute deux colonnes optionnelles.

| Colonne | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `summary` | TEXT | YES | NULL | Résumé compact ≤ 500 tokens du dernier batch compacté (REMPLACÉ à chaque compaction, pas cumulatif) |
| `last_compacted_at` | TIMESTAMP WITH TIME ZONE | YES | NULL | Timestamp de la dernière compaction réussie ; sert de lock optimiste |

RLS policy existante inchangée (`USING account_id = current_setting('app.current_account_id')::uuid`).

### 1.2 `chat_message`

Existant (F12/F18 — possède déjà `embedding VECTOR(1024)` et `metadata JSONB`). F57 ajoute :

| Colonne | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `compacted` | BOOLEAN | NO | FALSE | TRUE = message inclus dans un summary, exclu du recall futur (mais conservé pour audit P3) |

Index pgvector ajouté/recréé :
```sql
CREATE INDEX IF NOT EXISTS chat_message_embedding_hnsw_idx
  ON chat_message USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

RLS policy existante inchangée.

## 2. Tables nouvelles

### 2.1 `agent_entity_memory`

Stocke un fait stable par account et par entité business (Entreprise, Projet, Candidature, Indicateur).

| Colonne | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | UUID PK | NO | `gen_random_uuid()` | |
| `account_id` | UUID FK accounts(id) ON DELETE CASCADE | NO | | Scoping P2 RLS |
| `entity_type` | TEXT | NO | | Ex. `'Entreprise'`, `'Projet'`, `'Candidature'`, `'Indicateur'` |
| `entity_id` | UUID | NO | | FK logique (vérifiée applicative) vers la table métier |
| `summary` | TEXT | NO | | ≤ 800 tokens, factuel, sourcé via JSONB ci-dessous |
| `sources_used` | JSONB | NO | `'[]'::jsonb` | Liste de `source_id` ayant alimenté le summary (P1) |
| `last_updated_at` | TIMESTAMP WITH TIME ZONE | NO | `now()` | |
| `version` | INT | NO | 1 | Incrémenté à chaque update (logique referential P4) |

**Constraints** :
- `UNIQUE (account_id, entity_type, entity_id)` — un seul fait stable par tuple.
- INDEX `idx_agent_entity_memory_account_entity` ON `(account_id, entity_type, entity_id)`.
- RLS policy `agent_entity_memory_isolation` : `USING (account_id = current_setting('app.current_account_id', true)::uuid)`. Forcée en SELECT/INSERT/UPDATE/DELETE.

**Audit** : tout INSERT/UPDATE/DELETE déclenche une ligne `audit_log` avec `source_of_change='memory_system'`, `entity_type='AgentEntityMemory'`, `entity_id=<id>`.

### 2.2 `recall_log`

Trace toutes les opérations de recall (auto + tool) pour observabilité F60.

| Colonne | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | UUID PK | NO | `gen_random_uuid()` | |
| `agent_run_id` | UUID FK agent_run(id) ON DELETE SET NULL | YES | NULL | Trace cross F53 |
| `account_id` | UUID FK accounts(id) ON DELETE CASCADE | NO | | RLS |
| `thread_id` | UUID FK chat_thread(id) ON DELETE CASCADE | NO | | |
| `recall_type` | TEXT CHECK IN ('auto','tool') | NO | | `auto` = US1, `tool` = US2 |
| `query_hash` | TEXT | NO | | SHA-256 hex de la query (privacy-friendly, pas de query brute) |
| `top_k` | INT | NO | | K demandé |
| `top_scores` | JSONB | NO | | Liste `[{message_id, score}]` triée DESC ; max 10 entrées |
| `latency_ms` | INT | NO | | Latence end-to-end |
| `created_at` | TIMESTAMP WITH TIME ZONE | NO | `now()` | |

**Constraints** :
- INDEX `idx_recall_log_account_run` ON `(account_id, agent_run_id)` WHERE `agent_run_id IS NOT NULL`.
- INDEX `idx_recall_log_account_thread_time` ON `(account_id, thread_id, created_at DESC)`.
- RLS policy `recall_log_isolation` : `USING (account_id = current_setting('app.current_account_id', true)::uuid)`. INSERT autorisé pour applicative role, UPDATE/DELETE révoqués (consistent P3 audit append-only).

## 3. Migration Alembic 0036

Fichier : `backend/alembic/versions/0036_f57_memory_rag.py`.

Operations (ordre) :
1. `op.add_column('chat_thread', sa.Column('summary', sa.Text(), nullable=True))`.
2. `op.add_column('chat_thread', sa.Column('last_compacted_at', sa.TIMESTAMP(timezone=True), nullable=True))`.
3. `op.add_column('chat_message', sa.Column('compacted', sa.Boolean(), nullable=False, server_default=sa.text('false')))`.
4. `op.execute("CREATE INDEX IF NOT EXISTS chat_message_embedding_hnsw_idx ON chat_message USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)")`.
5. `op.create_table('agent_entity_memory', ...)` avec contraintes ci-dessus + RLS policy via `op.execute("ALTER TABLE agent_entity_memory ENABLE ROW LEVEL SECURITY; CREATE POLICY ...")`.
6. `op.create_table('recall_log', ...)` idem.
7. Revoke UPDATE/DELETE on `recall_log` from applicative role (audit append-only).
8. `op.execute("REVOKE UPDATE, DELETE ON recall_log FROM esg_app")` ou équivalent du role applicatif.

Downgrade : reverse ordre, `DROP INDEX chat_message_embedding_hnsw_idx`, drop columns, drop tables.

**Note conflit migration** : F56 sur `0035_f56_*`. F57 vise `0036` ; si ordre de merge inverse, `down_revision` ajusté à `0035_f56_*` au moment du second merge.

## 4. Pydantic models / SQLAlchemy ORM

### 4.1 ORM (SQLAlchemy 2.x style declarative_base)

```python
# app/agent/memory/models.py (NEW)

class AgentEntityMemory(Base):
    __tablename__ = "agent_entity_memory"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    sources_used: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    last_updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (UniqueConstraint("account_id", "entity_type", "entity_id"),)


class RecallLog(Base):
    __tablename__ = "recall_log"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_run.id", ondelete="SET NULL"), nullable=True)
    account_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    thread_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_thread.id", ondelete="CASCADE"), nullable=False)
    recall_type: Mapped[str] = mapped_column(Text, nullable=False)  # CHECK IN ('auto','tool')
    query_hash: Mapped[str] = mapped_column(Text, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    top_scores: Mapped[list] = mapped_column(JSONB, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
```

### 4.2 Pydantic schemas

```python
# app/chat/memory/schemas.py (EXTEND)

class EntityRef(BaseModel):
    type: Literal["Entreprise", "Projet", "Candidature", "Indicateur"]
    id: UUID
    label: str
    model_config = ConfigDict(extra="forbid")


class MemorySnapshotV2(BaseModel):
    """GET /me/chat/threads/{id}/memory response (FR-007)."""
    total_messages: int = Field(ge=0)
    recent_messages_count: int = Field(ge=0)  # = 15
    summary: str | None = None
    vector_index_size: int = Field(ge=0)
    last_compaction_at: datetime | None = None
    entities_referenced: list[EntityRef] = Field(default_factory=list)
    model_config = ConfigDict(extra="forbid")


# app/agent/handlers/recall_history.py (NEW)
class RecallHistoryArgs(BaseModel):
    """Tool LLM-callable (US2) — schema strict (P9)."""
    query: str = Field(..., min_length=1, max_length=256, description="Texte à rechercher dans l'historique du thread courant")
    limit: int = Field(default=5, ge=1, le=10, description="Nombre max de messages à retourner (1-10)")
    model_config = ConfigDict(extra="forbid")


class RecallHistoryResult(BaseModel):
    """Résultat ré-injecté en ToolMessage par le dispatcher F55."""
    matches: list["RecallHistoryMatch"]
    truncated: bool
    model_config = ConfigDict(extra="forbid")


class RecallHistoryMatch(BaseModel):
    message_id: UUID
    role: Literal["user", "assistant"]
    content_preview: str  # tronqué selon LLM_AGENT_RECALL_HISTORY_MAX_TOKENS
    score: float = Field(ge=0.0, le=1.0)
    created_at: datetime
    model_config = ConfigDict(extra="forbid")
```

## 5. State LangGraph (extension AgentState)

```python
# app/agent/state.py (MINIMAL ADD — F53 owns this file)

class AgentState(BaseModel):
    # ... existing F53 fields
    embedding_cache: dict[str, list[float]] = Field(default_factory=dict, exclude=True)
    """Per-turn cache (NFR-001 + R5). Key = f'{thread_id}:{sha256(query)}'. Excluded from checkpointer."""

    recall_log_entries: list[dict] = Field(default_factory=list, exclude=True)
    """Per-turn collected recall logs, flushed to DB at end of turn."""
```

## 6. Constitutional alignment

| Principle | Implementation in data model |
|---|---|
| P1 Sourcing | `agent_entity_memory.sources_used JSONB` retient les `source_id` |
| P2 RLS | Toutes les nouvelles tables portent `account_id NOT NULL` + RLS policy |
| P3 Audit | Compaction, entity_memory CRUD, forget RGPD écrivent `audit_log`. `recall_log` UPDATE/DELETE révoqués |
| P4 Versioning | `agent_entity_memory.version` incrémenté à chaque update (replace pas append) |
| P5 Money | F57 ne touche pas aux montants ; frontière forget RGPD documentée |
| P6 Indicateur pivot | Pas de duplication ESG par axe ; `entity_type='Indicateur'` reste un référencement |
| P7 No intermediary | Aucun rôle externe créé |
| P8 Sync | DB business reste source de vérité ; entity_memory est cache reproductible |
| P9 Tool-use | `RecallHistoryArgs` Pydantic strict avec `extra='forbid'`, bornes |
| P10 Bottom sheet | Aucun champ interactif ajouté au modèle |

## 7. Diagrammes (référence textuelle)

### 7.1 Recall flow (US1)

```
user_message
    ↓
recall_memory node
    ├─ load 15 last messages (chronological, compacted=False)
    ├─ if total > 15:
    │    ├─ get_or_compute embedding (cache)
    │    ├─ search_long_term (pgvector cosine, top_k=3, threshold=0.7)
    │    └─ insert in head with prefix "[Souvenirs pertinents]"
    └─ write recall_log (recall_type='auto')
```

### 7.2 Compaction flow (US6)

```
chat_message INSERT (count % 50 == 0 AND count >= 100)
    ↓
BackgroundTasks.add_task(compact_thread, thread_id, db)
    ↓
compact_thread (async)
    ├─ acquire lock (UPDATE chat_thread SET last_compacted_at WHERE ...)
    ├─ if 0 rows: abort (concurrent)
    ├─ load chunk: oldest 50 non-compacted messages
    ├─ LLM call: prompt système + chunk → summary (≤ 500 tokens)
    ├─ UPDATE chat_thread.summary = new_summary
    ├─ UPDATE chat_message SET compacted = TRUE WHERE id IN (...)
    ├─ write audit_log
    └─ done
```

### 7.3 Entity memory flow (US7)

```
dispatcher.MUTATION succeeds (F55)
    ↓
hook post_mutation
    ├─ enqueue BackgroundTasks.add_task(update_entity_memory, account_id, entity_type, entity_id)
    │
update_entity_memory (async)
    ├─ load existing summary (if any) + 5 last messages mentioning this entity + current DB state
    ├─ LLM call: prompt système + context → new_summary (≤ 800 tokens, sourced)
    ├─ UPSERT agent_entity_memory (incr version)
    └─ write audit_log
```

### 7.4 Forget flow (US4)

```
DELETE /me/chat/threads/{id}/memory (synchronous)
    ↓
ChatMemoryService.forget_thread_memory
    ├─ verify thread exists for current_account_id (else 404)
    ├─ UPDATE chat_message SET embedding=NULL WHERE thread_id=:id
    ├─ UPDATE chat_thread SET summary=NULL, last_compacted_at=NULL WHERE id=:id
    ├─ DOES NOT touch chat_message.content (P3)
    ├─ DOES NOT touch agent_entity_memory (account-wide, see Clarification Q3)
    ├─ write audit_log {action: 'memory_forget', source_of_change: 'memory_system'}
    └─ return 200 OK
```
