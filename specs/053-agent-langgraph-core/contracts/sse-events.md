# Contract — SSE events protocol

**Feature** : F53 Agent LangGraph Core
**Endpoint** : `POST /messages` (existant F13, modifié pour appeler `run_agent` quand `LLM_AGENT_MODE='langgraph'`)
**Format** : Server-Sent Events (`text/event-stream`).

## Format général

```
event: <event_type>
data: <json_payload>

```

(Note : ligne vide finale obligatoire entre events.)

## Events

### `token` (existant F13, conservé)

Émis pour chaque chunk de texte LLM en streaming.

**Payload** :
```json
{
  "text": "Voici une partie de la réponse..."
}
```

**Frontend** : F41 concatène ces tokens dans la bulle assistant en cours.

---

### `tool_invoke` (nouveau F53)

Émis quand un tool de catégorie `ask_*` ou `show_*` doit être exécuté côté front (bottom sheet ou viz).

**Payload** :
```json
{
  "tool_call_id": "call_abc123",
  "tool_name": "ask_qcu",
  "arguments": {
    "label": "Quel est le montant prévu ?",
    "options": ["< 10M FCFA", "10-50M FCFA", "> 50M FCFA"],
    "field_path": "projet.montant_estime"
  }
}
```

**Frontend** : F41 dispatche vers F39 (bottom sheet engine) pour `ask_*` et F40 (viz library) pour `show_*`. Quand l'utilisateur valide, le frontend `POST /messages` à nouveau avec la valeur dans `context_json.user_response_to_tool_call_id`.

---

### `mutation` (nouveau F53)

Émis après un dispatch DB réussi (`update_*`, `create_*`, `delete_*`).

**Payload** :
```json
{
  "tool_call_id": "call_def456",
  "entity": "projet",
  "action": "create",
  "id": "5bc4d3a2-1234-5678-9abc-def012345678",
  "snapshot": {
    "id": "...",
    "nom": "Panneaux solaires Abidjan",
    "puissance_kwc": 50,
    "montant_estime": {"amount": "25000000", "currency": "XOF"}
  },
  "audit_log_id": "..."
}
```

**Frontend** : F41 émet sur l'EventBus → stores Pinia (Profil/Projets/Indicateurs) refresh sans reload.

---

### `validation_retry` (nouveau F53)

Émis quand un tool call est rejeté et un retry va être effectué (debug + transparence utilisateur).

**Payload** :
```json
{
  "retry_count": 1,
  "tool_name": "create_projet",
  "error_summary": "field 'severity' not in enum ['low', 'medium', 'high']"
}
```

**Frontend** : F41 peut afficher discrètement « ESG Mefali corrige... » (UX optionnelle, F55 polishera).

---

### `error` (existant F13, étendu F53)

Émis quand une erreur non-récupérable survient.

**Payload** :
```json
{
  "code": "validation_failed_after_retries",
  "message": "Je n'arrive pas à formaliser cette action — peux-tu reformuler ?",
  "agent_run_id": "..."
}
```

Codes possibles :
- `validation_failed_after_retries` (FR-006)
- `dispatch_db_error` (constraint violation)
- `llm_error` (upstream LLM 5xx)
- `timeout` (`LLM_AGENT_TIMEOUT_S` dépassé)
- `internal` (bug serveur)

**Frontend** : F41 affiche une bulle assistant d'erreur stylée + bouton « Réessayer ».

---

### `done` (existant F13, étendu F53)

Émis à la toute fin d'un tour, signalant que le SSE va se fermer.

**Payload** :
```json
{
  "final_text": "J'ai créé le projet. Tu peux le retrouver dans Profil → Projets.",
  "agent_run_id": "...",
  "tokens_used": {"in": 1234, "out": 567}
}
```

**Frontend** : F41 finalise la bulle, ferme l'EventSource, affiche le compteur tokens (debug toggle).

## Ordering

Pour un tour donné, l'ordre des events est :

```
[token*]                 # streaming texte (peut être vide si tool-only)
[validation_retry]?      # 0-2 fois si retries
[tool_invoke]*           # si tools ask_*/show_* (peut suivre des tokens)
[mutation]*              # si tools update/create/delete réussis
[error]?                 # uniquement en cas d'échec terminal
done                     # toujours, sauf cancellation
```

En cas de cancellation client : aucun `done` n'est envoyé, le SSE se ferme abruptement (cf. FR-012). Le serveur marque `agent_run.status='cancelled'` côté DB.

## Idempotence

Le frontend doit traiter chaque event comme idempotent (un même `tool_call_id` ne sera jamais émis deux fois pour le même run). Si une déduplication est nécessaire (cas resume après crash), l'ID `agent_run_id` permet de filtrer les events d'un run précédent.

## Compat F13

Les nouveaux events (`tool_invoke`, `mutation`, `validation_retry`) sont **additifs** : un client F41 pré-F53 ignore silencieusement les events qu'il ne connaît pas. La cohérence finale est livrée par F55.
