# Data Model — F41 Chat Conversational Layer

F41 ne crée **aucune table backend**. Les entités persistées (`chat_thread`, `chat_message`, `chat_thread_event`, `chat_memory_*`) sont fournies par F12 et F18. Ce document décrit uniquement les **entités UI / store** consommées par la couche frontend, et leur mapping aux contrats backend.

## 1. Entités frontend (Pinia / TypeScript)

### 1.1 `ChatThreadSummary`

Représentation d'un thread dans la sidebar.

| Champ | Type | Source | Notes |
|-------|------|--------|-------|
| `id` | `string` (UUID) | `GET /me/chat/threads` | clé primaire |
| `title` | `string` | idem | titre auto-généré côté backend ou « Nouveau chat » par défaut |
| `lastMessageAt` | `string` (ISO 8601) | idem | tri DESC dans la sidebar |
| `createdAt` | `string` (ISO 8601) | idem | |
| `archived` | `boolean` | idem | threads archivés masqués par défaut |

### 1.2 `ChatMessage`

Représentation d'un message dans l'historique.

| Champ | Type | Source | Notes |
|-------|------|--------|-------|
| `id` | `string` (UUID) | `GET /me/chat/threads/{id}/messages` ou stream `event: message_done` | |
| `threadId` | `string` (UUID) | idem | |
| `role` | `'user' \| 'assistant' \| 'system'` | idem | `system` masqué côté UI mais conservé en mémoire |
| `content` | `string` | idem | Markdown brut (avant sanitize) |
| `payload` | `MessagePayload \| null` | idem | charge structurée (viz, sheet result, error) |
| `createdAt` | `string` (ISO 8601) | idem | |
| `sequenceId` | `number` | stream frames | utilisé en dedup pendant streaming |
| `streaming` | `boolean` | flag local | true tant que `event: message_done` non reçu |

### 1.3 `MessagePayload` (discriminated union)

```ts
type MessagePayload =
  | { kind: 'viz';        tool: 'kpi' | 'line' | 'area' | 'bar' | 'radar' | 'gauge' | 'pie' | 'donut' | 'mermaid' | 'table' | 'map'; data: unknown }
  | { kind: 'sheet_result'; sheetId: string; selection: unknown }   // résumé textuel + sélection brute
  | { kind: 'error';      code: string; message: string; retryOf: string /* messageId */ }
```

`unknown` est borné par le contrat de chaque composant viz F40 (cf. `specs/040-viz-library/contracts/component-api.md`).

### 1.4 `StreamingState`

État interne d'un envoi en cours.

```ts
interface StreamingState {
  threadId: string
  userMessageId: string         // déjà inséré côté UI (optimistic)
  assistantMessageId: string    // créé côté UI dès le 1er token
  abortController: AbortController
  seqSeen: Set<number>          // dedup
  partialContent: string        // buffer Markdown courant
  startedAt: number             // perf.now()
  firstTokenAt: number | null
  retryCount: number            // backoff reconnect SSE
}
```

### 1.5 `ChatError`

Une erreur affichée comme bulle.

```ts
interface ChatError {
  messageId: string             // id de la bulle erreur
  retryOf: { content: string; payload: unknown | null }   // ce qu'il faut rejouer
  code: 'validation' | 'timeout' | 'network' | 'forbidden' | 'unknown'
  message: string               // FR
}
```

### 1.6 `EventBusEvent`

Événement diffusé par `useChatEventBus`.

```ts
interface EventBusEvent {
  eventType: 'entity_updated' | 'entity_created' | 'entity_deleted' | 'memory_updated'
  entityType: string            // ex. 'entreprise', 'projet', 'indicateur_value'
  entityId: string
  fieldsUpdated?: string[]
  source: 'llm' | 'manual' | 'import' | 'admin'
  ts: string                    // ISO 8601
}
```

Mappe directement les events `/me/events` SSE de F18 + les broadcasts internes Pinia.

### 1.7 `MemorySnapshot`

```ts
interface MemorySnapshot {
  threadId: string
  size: number                  // tokens approximatifs ou nb d'entrées
  entries: Array<{ kind: string; preview: string; entityRef?: string }>
  fetchedAt: string
}
```

## 2. Validation rules (côté UI)

- `ChatMessage.content` : longueur max 32 000 caractères côté envoi (rejet local + message UI), aligné sur la limite backend Pydantic.
- `payload.kind === 'viz'` : si la charge ne valide pas le contrat F40 du composant ciblé, fallback sur `<MessageError>` avec `code: 'validation'`.
- `EventBusEvent.source === 'llm'` : ignoré par les listeners qui re-déclenchent l'orchestrateur LLM (anti-loop P8).
- `sequenceId` strictement croissant pour un `assistantMessageId` donné ; un id déjà vu dans `seqSeen` est ignoré.

## 3. State transitions — machine streaming

```
┌──────┐   send()         ┌────────────┐
│ idle │ ────────────────▶│ streaming  │
└──────┘                  └─────┬──────┘
   ▲                            │
   │                            │ tool_invoke (F39 sheet)
   │                            ▼
   │                     ┌──────────────────┐
   │   message_done      │  awaiting_sheet  │
   │ ◀───────────────────┤                  │
   │                     └────┬─────────────┘
   │                          │ sheet validate / freetext
   │                          ▼
   │                     ┌────────────┐
   └─────────────────────┤ streaming  │
                         └────────────┘
```

États additionnels : `error` (pipeline LLM échoue → bulle erreur, retry possible) et `cancelled` (utilisateur ferme la page → `abortController.abort()`).

## 4. Mapping aux entités backend (référence)

| UI entity | Backend table (F12) | Notes |
|-----------|---------------------|-------|
| `ChatThreadSummary` | `chat_thread` | RLS par `account_id`, FK `user_id` |
| `ChatMessage` | `chat_message` | role, content, payload_json, sequence_id |
| `MemorySnapshot` | `chat_memory_snapshot` (F18) | lecture seule côté F41 |
| `EventBusEvent` (entity_*) | flux SSE `/me/events` (F18) | non persisté côté F41 |

Aucune écriture directe : F41 n'utilise **que** les endpoints REST/SSE déjà publiés.
