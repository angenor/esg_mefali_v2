# F14 — SSE Events Contract (extension de F13)

F14 ajoute 3 nouveaux event types au flux SSE existant `/chat/messages` (F13). Le contrat F13 (`text_delta`, `message_done`, `error`) reste **intact**.

## Enveloppe générale

Format identique à F13 :

```
event: <event_type>
data: <JSON payload sur une ligne>
\n\n
```

Le frontend doit ignorer silencieusement tout `event_type` inconnu (forward-compatibilité).

## Nouveaux events

### 1. `thinking`

Émis avant chaque étape coûteuse pour permettre à l'UI d'afficher un état "réflexion".

```
event: thinking
data: {"step": "<step_name>"}
```

Valeurs possibles de `step` :

| Valeur | Quand |
|--------|-------|
| `classifying` | Avant l'appel du classifier d'intention |
| `selecting_tools` | Avant le sélecteur |
| `calling_llm` | Avant chaque appel LLM principal (initial + retries) |
| `validating` | Avant la validation Pydantic |
| `retrying` | Avant un retry suite à erreur de validation |

### 2. `tool_call_started`

Émis dès qu'un payload validé déclenche l'exécution d'un handler tool.

```
event: tool_call_started
data: {
  "tool_name": "<string>",
  "call_id": "<uuid v4>"
}
```

- `call_id` est un identifiant côté serveur, à corréler avec `tool_call_completed`.
- `tool_name` correspond à une clé de `TOOL_REGISTRY`.

### 3. `tool_call_completed`

Émis à la fin de l'exécution d'un handler tool (succès ou erreur).

```
event: tool_call_completed
data: {
  "tool_name": "<string>",
  "call_id": "<uuid v4>",
  "status": "ok" | "validation_error" | "handler_error" | "timeout",
  "latency_ms": <int>,
  "retries": <int 0..2>,
  "result_preview": <object | null>,
  "error_detail": <object | null>
}
```

- `result_preview` : projection sûre du résultat (non-PII, ≤ 500 octets) — peut être `null`.
- `error_detail` :
  - Pour `validation_error` : `{"field": "...", "received": ..., "expected": "..."}`.
  - Pour `handler_error` : `{"type": "...", "message": "..."}` (message tronqué à 200 caractères).
  - Pour `timeout` : `{"timeout_ms": <int>}`.
  - Pour `ok` : `null`.

## Ordre garanti pour un tour réussi

```
event: thinking      data: {"step": "classifying"}
event: thinking      data: {"step": "selecting_tools"}
event: thinking      data: {"step": "calling_llm"}
event: thinking      data: {"step": "validating"}
event: tool_call_started   data: {"tool_name": "...", "call_id": "..."}
event: tool_call_completed data: {"tool_name": "...", "call_id": "...", "status": "ok", ...}
event: text_delta    data: {"delta": "..."}
event: message_done  data: {"message_id": "..."}
```

## Ordre pour un tour avec retry réussi

```
event: thinking      data: {"step": "classifying"}
event: thinking      data: {"step": "calling_llm"}
event: thinking      data: {"step": "validating"}
event: thinking      data: {"step": "retrying"}
event: thinking      data: {"step": "calling_llm"}
event: thinking      data: {"step": "validating"}
event: tool_call_started   ...
event: tool_call_completed data: {... "status": "ok", "retries": 1}
event: text_delta    ...
event: message_done  ...
```

## Ordre pour un fallback texte (3 essais ratés)

```
event: thinking      data: {"step": "classifying"}
event: thinking      data: {"step": "calling_llm"}
event: thinking      data: {"step": "validating"}
event: thinking      data: {"step": "retrying"}
event: thinking      data: {"step": "calling_llm"}
event: thinking      data: {"step": "validating"}
event: thinking      data: {"step": "retrying"}
event: thinking      data: {"step": "calling_llm"}
event: thinking      data: {"step": "validating"}
event: text_delta    data: {"delta": "Je n'arrive pas à formaliser cette action — peux-tu reformuler ?"}
event: message_done  data: {"message_id": "..."}
```

Aucun `tool_call_started` n'est émis dans ce cas.

## Erreurs

L'event `error` (F13) reste valide pour les erreurs irrécupérables (LLM indisponible, panne DB). Le pipeline F14 préfère **ne pas** émettre `error` et privilégie le fallback texte + log d'incident dans `tool_call_log` quand c'est possible.

## Compatibilité

- Tout client F13 fonctionnel continuera de fonctionner sans modification.
- Le client F14-aware peut afficher un indicateur de progression riche en utilisant `thinking` + `tool_call_*`.
