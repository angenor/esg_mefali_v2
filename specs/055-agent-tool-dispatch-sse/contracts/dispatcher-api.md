# Dispatcher API Contract — F55

Date: 2026-05-06

API publique du module `app/agent/dispatcher.py` consommée par le runner LangGraph et les tests d'intégration.

## `dispatch(call, state, db, *, mutation_ctx, dry_run, hooks) -> ToolDispatchResult`

```python
async def dispatch(
    call: ValidatedToolCall,
    state: AgentState,
    db: AsyncSession,
    *,
    mutation_ctx_factory: Callable[[ValidatedToolCall], MutationCtx],
    dry_run: bool = False,
    hooks: DispatchHooks | None = None,
) -> ToolDispatchResult:
    ...
```

### Comportement

1. **Idempotency check** : calcule `idempotency_key = sha256(f"{state.account_id}:{state.agent_run_id}:{call.id}").hexdigest()[:32]`. SELECT FOR SHARE sur `tool_call_log`. Si trouvé → retourne le `ToolDispatchResult` reconstruit, ne ré-exécute pas.
2. **Hard cap check** : si `state.tool_calls_count_in_turn >= 10` → retourne `ToolDispatchResult(kind='error', error_summary='tool_calls_cap_reached', status='error')`.
3. **Categorization** : `category = TOOL_REGISTRY[call.name].category`.
4. **Dispatch par catégorie** :
   - **ASK / SHOW** : retourne `ToolDispatchResult(kind='frontend_event', output={arguments,...}, status='ok')`.
   - **MUTATION** :
     a. Si `requires_confirmation=True` ET pas déjà confirmé → stocke `pending_confirmation` dans `agent_run.metadata`, retourne `ToolDispatchResult(kind='frontend_event', status='pending_confirmation', output=ask_yes_no_payload)`.
     b. Sinon : rate limit check → si refusé, retourne `kind='error', status='rate_limited'`.
     c. Sinon : ouvre transaction DB, instancie `MutationCtx`, exécute pre-hooks, appelle handler, audit_logger, post-hooks. Si dry_run → ROLLBACK forcé. Sinon COMMIT. Retourne `kind='mutation_result'` avec entity_type/entity_id/fields_updated/audit_log_id.
   - **READ** : exécute handler, sérialise via `serialize_read_result(result, budget_tokens=...)`, retourne `kind='tool_message', output={'content': serialized_str}`.
5. **Persist** : INSERT/UPDATE row `tool_call_log` avec `status, dispatch_result_kind, idempotency_key, agent_run_id`.

### Erreurs

| Cas | `kind` | `status` | `error_summary` |
|---|---|---|---|
| Handler missing | `error` | `error` | `handler_not_registered` |
| Rate limit dépassé | `error` | `rate_limited` | `rate_exceeded:<tool_name>` |
| Rate limit store down | `error` | `error` | `rate_limit_unavailable` |
| RLS refus (cross-tenant) | `error` | `error` | `entity_not_found` (404 logique, pas 403) |
| Handler exception | `error` | `error` | sanitized exc message (pas d'UUID brut) |
| Validation retry exhausted (P9) | géré en amont par `validate_payload` node, pas dispatch |
| Hard cap atteint | `error` | `error` | `tool_calls_cap_reached` |
| Confirmation expirée | `error` | `confirmation_expired` | `confirmation_expired` |
| User clique "Non" | `frontend_event` | `cancelled_by_user` | — |

### Transaction & RLS

- Une transaction DB par mutation handler (pas par tool call ASK/SHOW/READ).
- `SET LOCAL "app.current_account_id" = ?` au début de la transaction.
- Handler + audit_log écrits dans la même transaction.
- Si dry_run : transaction `BEGIN; ... ROLLBACK;` (jamais COMMIT).

## Décorateur `@mutation_handler`

```python
def mutation_handler(
    tool_name: str,
    *,
    requires_confirmation: bool = False,
) -> Callable[[Handler], Handler]:
    """
    Enregistre un handler pour un tool MUTATION dans MUTATION_HANDLERS dict.
    Le handler signature MUST être :
       async def handler(args: BaseModel, ctx: MutationCtx) -> MutationResult
    """
```

Au boot (`startup_event` FastAPI) :
- Vérifie que chaque tool `ToolCategory.MUTATION` a un handler enregistré → sinon `RuntimeError('handler missing for {tool_name}')` exit 1.
- Vérifie que chaque tool dans le registry a un `category` non null → sinon `RuntimeError('category missing for {tool_name}')` exit 1.

## Hooks

```python
class DispatchHooks(BaseModel):
    before: list[Callable[[ValidatedToolCall, AgentState], Awaitable[None]]]
    after: list[Callable[[ValidatedToolCall, ToolDispatchResult], Awaitable[None]]]
```

- Les hooks sont appelés best-effort : exception → log warning, dispatch continue.
- Décorateurs `@before_dispatch` et `@after_dispatch` enregistrent dans `_HOOKS_REGISTRY`.

## Rate Limit Store

```python
class RateLimitStore(Protocol):
    async def check_and_increment(
        self,
        account_id: UUID,
        tool_name: str,
        limit_per_minute: int,
    ) -> RateLimitDecision: ...

    async def health_check(self) -> bool: ...
```

Implémentations :
- `InMemoryRateLimitStore` (dev single-worker, bounded LRU 1000 keys).
- `RedisRateLimitStore` (prod multi-worker, Lua atomic INCR+EXPIRE).

Sélection : `LLM_AGENT_RATE_LIMIT_BACKEND={memory,redis}` (défaut `memory`).

## Idempotency

```python
def compute_idempotency_key(account_id: UUID, agent_run_id: UUID, call_id: str) -> str:
    raw = f"{account_id}:{agent_run_id}:{call_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


async def find_existing(db: AsyncSession, account_id: UUID, key: str) -> ToolCallLog | None:
    ...
```

## Confirmation flow

```python
async def store_pending_confirmation(
    db: AsyncSession,
    agent_run_id: UUID,
    pending: PendingConfirmation,
) -> None: ...

async def consume_confirmation(
    db: AsyncSession,
    agent_run_id: UUID,
    call_id: str,
    user_response: Literal["yes", "no"],
) -> PendingConfirmation | None:
    """
    Retourne la PendingConfirmation si elle existe ET non expirée ET user_response='yes'.
    Sinon None ; supprime la pending dans tous les cas (TTL ou réponse).
    """
```

## Exemples handlers

```python
@mutation_handler("update_company_profile")
async def update_company_profile_handler(
    args: UpdateCompanyProfileArgs,
    ctx: MutationCtx,
) -> MutationResult:
    entreprise = await ctx.db.get(Entreprise, args.entreprise_id)
    if entreprise is None:
        raise EntityNotFoundError("entreprise_not_found")
    diffs = compute_diff(entreprise, args)
    await update_entreprise(ctx.db, entreprise, args)
    await ctx.audit_logger.append_many(
        diffs,
        source_of_change="llm",
        tool_call_id=ctx.tool_call_log_id,
        agent_run_id=ctx.agent_run_id,
    )
    await ctx.event_bus_publisher(
        ctx.account_id,
        "entity_updated",
        {"entity_type": "Entreprise", "entity_id": str(entreprise.id), "fields_updated": [d.field for d in diffs], "source": "llm"},
    )
    return MutationResult(
        entity_type="Entreprise",
        entity_id=entreprise.id,
        fields_updated=[d.field for d in diffs],
        snapshot=entreprise_to_snapshot(entreprise),
    )


@mutation_handler("delete_project", requires_confirmation=True)
async def delete_project_handler(args: DeleteProjectArgs, ctx: MutationCtx) -> MutationResult:
    ...
```
