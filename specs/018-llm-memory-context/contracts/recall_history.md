# Contract — Tool `recall_history`

**Module**: `app/chat/memory/recall_history_tool.py`
**Date**: 2026-04-29

## Schéma Pydantic

```python
class RecallHistoryArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=500)
    k: int = Field(default=5, ge=1, le=10)
```

## Enregistrement registry (F14)

```python
RECALL_HISTORY_TOOL = tool(
    name="recall_history",
    description="Recherche dans l'historique ancien de la conversation actuelle (au-delà des 15 derniers messages) un fragment lié à la question.",
    use_when="L'utilisateur fait référence à un sujet, projet, ou décision discuté précédemment dans la même conversation et qui n'apparaît pas dans les 15 derniers messages.",
    dont_use_when="La réponse se trouve dans les 15 derniers messages, OU l'utilisateur démarre un nouveau sujet, OU le thread contient moins de 16 messages.",
    schema=RecallHistoryArgs,
    positive_examples=(
        {"query": "biogaz Sénégal", "k": 5},
        {"query": "ratio CA effectifs discuté en début de conversation"},
    ),
    negative_examples=(
        {"query": ""},
        {"query": "ab"},
    ),
)
```

## Signature exécution

```python
def execute_recall_history(
    db: Session,
    *,
    account_id: UUID,
    thread_id: UUID,
    args: RecallHistoryArgs,
) -> list[RecallHit]:
    ...
```

## Comportement

1. Si `len(args.query.strip()) < 3` → retourner `[]` (FR-016).
2. Calculer l'embedding de la query via `app.embeddings_client.embed([query])`.
3. Identifier les IDs des 15 derniers messages du thread (à exclure).
4. Exécuter la requête SQL paramétrée :

   ```sql
   SELECT id, thread_id, role, content, payload_json, created_at,
          1 - (embedding <=> CAST(:qvec AS vector)) AS similarity
   FROM chat_message
   WHERE account_id = :aid
     AND thread_id = :tid
     AND embedding IS NOT NULL
     AND deleted_at IS NULL
     AND id NOT IN :recent_ids
     AND role IN ('user', 'assistant')
   ORDER BY embedding <=> CAST(:qvec AS vector) ASC
   LIMIT :k;
   ```

5. Construire un `RecallHit` par ligne avec :
   - `snippet` = `content[:240]` ou `payload_json.label/title[:240]` si payload présent.
   - `similarity` = `1 - distance_cosinus`.

## Pré-conditions

- RLS positionné sur la session.
- Index `idx_chat_message_embedding` existe (migration 0013).

## Post-conditions

- Liste de longueur ≤ k.
- Tous les hits ont `account_id == :aid` et `thread_id == :tid` (RLS + filtre explicite).
- Tous les hits ont `id NOT IN (15 derniers messages)`.
- Tri par similarité descendante.

## Exceptions

- `VoyageError` si Voyage indisponible — propagée au caller (le sélecteur F14 gère le fallback).
- Aucun raise sur résultat vide (retourne `[]`).

## Performance attendue

- p95 < 200 ms (SC-002) sur thread de 50 messages.
- `SET LOCAL ivfflat.probes = 10;` positionné avant la requête (option qualité).

## Tests obligatoires

- `test_recall_history_short_query_returns_empty` : query < 3 chars → `[]`, pas d'appel embedding.
- `test_recall_history_excludes_recent_15` : thread de 50 messages, recall renvoie hors top 15.
- `test_recall_history_filters_by_thread` : recall sur thread A ne renvoie aucun message du thread B.
- `test_recall_history_filters_by_account` : compte A invoque recall, aucun message du compte B.
- `test_recall_history_orders_by_similarity` : 5 messages dont 1 très proche → ce hit est en position 0.
- `test_recall_history_extracts_payload_label` : message avec payload visualisation → snippet contient le label.
- `test_recall_history_respects_k_limit` : 50 messages pertinents, `k=5` → retourne exactement 5.
- `test_recall_history_skips_null_embeddings` : message avec `embedding IS NULL` jamais retourné.

## Gating au sélecteur F14

Le tool n'est ajouté à la liste exposée au LLM que si `count_messages_in_thread > 15`. Le `tool_selector` reçoit cette information via le caller orchestrateur.
