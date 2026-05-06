# Contract — LangGraph node `recall_memory`

## Localisation

`backend/app/agent/nodes/recall_memory.py` (RÉÉCRITURE TOTALE — F54 a livré un squelette qui chargeait simplement les 15 derniers messages SQL).

## Signature

```python
async def node(state: AgentState) -> dict[str, Any]:
    """
    Charge le contexte mémoire pour le tour courant (US1).
    Retourne un dict de patches pour le state LangGraph.

    Comportement :
      1. Charge les LLM_AGENT_MEMORY_RECENT_COUNT (=15) derniers messages
         (role IN ('user','assistant'), compacted=False), ordre chronologique ASC.
      2. Si total messages thread > 15:
           - get_or_compute embedding de la user_message du tour (cache state.embedding_cache).
           - search_long_term(thread_id, account_id, embedding, exclude=recent_ids,
                              limit=LLM_AGENT_MEMORY_TOP_K (=3),
                              threshold=LLM_AGENT_MEMORY_THRESHOLD (=0.7)).
           - Si > 0 results: insère en tête avec prefix "[Souvenirs pertinents...]"
      3. Si chat_thread.summary IS NOT NULL: insère en TOUT premier (avant souvenirs)
         avec prefix "[Résumé compacté des messages anciens]".
      4. Écrit recall_log avec recall_type='auto', latency mesurée.

    Output dict patches:
      - "messages": list[BaseMessage]  (court terme + long terme + summary si dispo)
      - "recall_log_entries": list[dict]  (à flusher en fin de turn)
      - "embedding_cache": dict (mis à jour, in-place via state)
    """
```

## Inputs (lecture sur AgentState)

- `state.thread_id: UUID` — fourni par F53.
- `state.account_id: UUID` — fourni par F53.
- `state.user_message: str` — message courant de l'utilisateur (pour embedding).
- `state.agent_run_id: UUID` — pour `recall_log.agent_run_id`.
- `state.embedding_cache: dict[str, list[float]]` — cache transient (vide en début de tour).

## Outputs (patches à appliquer)

```python
{
    "messages": [BaseMessage, ...],            # Système-prefixed pour bloc summary, AIMessage/HumanMessage pour le reste
    "recall_log_entries": [
        {
            "recall_type": "auto",
            "thread_id": ...,
            "query_hash": "abcd...",
            "top_k": 3,
            "top_scores": [{"message_id": ..., "score": 0.82}, ...],
            "latency_ms": 145
        }
    ],
}
```

## Format des messages insérés

### Bloc summary (si `chat_thread.summary IS NOT NULL`)

```
SystemMessage(content="[Résumé compacté des messages anciens]\n" + chat_thread.summary)
```

### Bloc souvenirs (si recall long terme retourne > 0 résultats)

```
SystemMessage(content="[Souvenirs pertinents d'échanges précédents]\n" +
              "\n---\n".join([f"({m.role}, {m.created_at:%Y-%m-%d}): {m.content}" for m in long_term_msgs]))
```

### Bloc court terme (15 derniers, toujours présent si > 0 messages)

```
[HumanMessage(content=...) | AIMessage(content=...) for each in recent]
```

Ordre final dans `messages` :
1. Summary (si dispo)
2. Souvenirs long terme (si dispo)
3. Court terme chronologique
4. La nouvelle user_message (poussée par F53 plus loin dans le graph)

## Mode dégradé (FR-014)

- Si Voyage API échoue : long_term skipped, log warning, court terme + summary OK.
- Si pgvector cosine échoue : idem.
- Aucune levée d'exception remontée à l'utilisateur (NFR-008).

## Test cases

| ID | Given | When | Then |
|---|---|---|---|
| RM-001 | Thread 5 msgs (< 15) | node(state) | retourne 5 messages chronologiques, pas d'embedding call, pas de recall_log entry de type 'auto' |
| RM-002 | Thread 50 msgs, mention "solaire" dans msgs 1-10 uniquement, query="solaire" | node(state) | 15 derniers + 3 souvenirs longs ≥ 0.7 + 1 recall_log entry |
| RM-003 | Thread 100 msgs, summary défini, query="autre sujet" sans matchs | node(state) | summary block + 15 derniers + 0 souvenirs |
| RM-004 | Thread 30 msgs, Voyage API down | node(state) | 15 derniers, log warning, pas d'exception, recall_log non écrit |
| RM-005 | Thread 100 msgs, pgvector down | node(state) | 15 derniers, log warning, pas d'exception |
| RM-006 | Thread A et Thread B même account, query dans Thread B | node(state) sur Thread B | 0 message du Thread A (RLS + scope thread_id) |

## Performance

- p95 < 300 ms (1 embed + 1 cosine search HNSW + 15 reads).
- Si cache hit (recall_history même tour) : p95 < 100 ms.
