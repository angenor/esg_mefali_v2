# Contract — Tool LLM `recall_history`

## Description LLM

Tool exposé au LLM via le dispatcher F55 (catégorie `READ`). Permet à l'agent de chercher explicitement dans l'historique du thread courant quand le recall automatique du nœud `recall_memory` n'a rien remonté ou quand l'agent veut une recherche ciblée.

## Schéma Pydantic strict (P9)

```python
# app/agent/handlers/recall_history.py

class RecallHistoryArgs(BaseModel):
    """
    Arguments du tool recall_history.

    use when:
      - L'utilisateur réfère à un sujet ancien que tu ne retrouves pas dans le contexte courant
        ("rappelle ce qu'on disait sur X", "tu te souviens de Y ?")
      - Tu as besoin d'une donnée spécifique citée plus tôt (chiffre, nom, date)

    don't use when:
      - Le sujet est déjà dans les 15 derniers messages du contexte (gaspillage)
      - L'utilisateur demande une nouvelle information non évoquée auparavant
      - Tu veux chercher dans un AUTRE thread (impossible — scope strict thread courant)

    examples:
      - positive: User says "Reprends le budget rénovation qu'on avait évoqué" →
                  recall_history(query="budget rénovation", limit=5)
      - negative: User asks for the first time about ROI → DON'T call recall_history
                  (rien à rappeler).
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Texte à chercher dans l'historique du thread courant (en français).",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Nombre max de messages à retourner (1-10, default 5).",
    )

    model_config = ConfigDict(extra="forbid")
```

## Comportement (handler)

```python
async def handle_recall_history(args: RecallHistoryArgs, ctx: ToolCtx) -> RecallHistoryResult:
    """
    1. Récupère thread_id et account_id depuis ctx.
    2. Calcule (ou récupère du cache) l'embedding de args.query (NFR-008).
    3. search_long_term(thread_id, account_id, query_embedding, exclude=[], limit=args.limit, threshold=0.0)
       (threshold=0.0 ici car le LLM a explicitement demandé : pas de filtre seuil).
    4. Tronque chaque content_preview selon LLM_AGENT_RECALL_HISTORY_MAX_TOKENS (default 800 tokens budget total).
    5. Écrit recall_log avec recall_type='tool', latency mesurée.
    6. Retourne RecallHistoryResult.
    """
```

## Schéma de retour

```python
class RecallHistoryMatch(BaseModel):
    message_id: UUID
    role: Literal["user", "assistant"]
    content_preview: str  # tronqué
    score: float = Field(ge=0.0, le=1.0)  # cosine similarity
    created_at: datetime
    model_config = ConfigDict(extra="forbid")


class RecallHistoryResult(BaseModel):
    matches: list[RecallHistoryMatch]
    truncated: bool  # true si content_preview a été tronqué
    model_config = ConfigDict(extra="forbid")
```

## Dispatcher F55 — catégorie READ

- Le dispatcher exécute le handler en transaction read-only.
- Le résultat est sérialisé via `read_serializer` (existant F55) en `ToolMessage` JSON tronqué selon budget tokens (`LLM_AGENT_RECALL_HISTORY_MAX_TOKENS=800`).
- Le `ToolMessage` est ré-injecté au tour suivant comme contexte LLM (cohérent F55 décision Q4).

## Validation P9

- Validateur F14 vérifie le schéma Pydantic ; `extra='forbid'` rejette tout argument non listé.
- `query` vide ou > 256 chars ⇒ rejet, max 2 retries (cohérent P9).
- Pas de pré-condition `cite_source` requise (le tool n'émet pas d'assertion factuelle, il restitue des messages stockés).

## Test cases (Acceptance)

| ID | Given | When | Then |
|---|---|---|---|
| RH-001 | Thread 50 msgs avec mention "budget" anciennement | LLM call recall_history(query="budget") | 5 matches retournés, dispatcher renvoie ToolMessage |
| RH-002 | Tool call avec `query=""` | dispatcher reçoit | rejet validateur, retry max 2 |
| RH-003 | Tool call avec `limit=20` | dispatcher reçoit | rejet validateur (`le=10`) |
| RH-004 | Thread A account X / Thread B account X, agent dans Thread B call recall_history | search effectué | 0 résultats du Thread A (anti-fuite cross-thread) |
| RH-005 | Tool call avec `extra={"foo":"bar"}` | dispatcher reçoit | rejet (`extra='forbid'`) |
| RH-006 | Tool call dans un tour où recall_memory auto a déjà calculé l'embedding de la même query | dispatcher exécute | 1 seul appel Voyage (cache hit, NFR-008) |

## Anti-fuite cross-thread (US7)

`search_long_term()` MUST inclure `WHERE thread_id = :thread_id AND account_id = :account_id` dans la query SQL — vérifié par le test `RH-004`.

## Performance

- p95 latence handler < 200 ms (1 embed + 1 cosine search top-K).
- Si cache hit (US8) : p95 < 50 ms.
