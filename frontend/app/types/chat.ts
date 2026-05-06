/**
 * Types partagés du module Chat (F41).
 *
 * Source : specs/041-chat-conversational-layer/data-model.md.
 * F41 ne crée aucune table backend ; ces types décrivent uniquement les entités
 * UI consommées par les stores Pinia, composables et composants Vue.
 */

// -- Threads -----------------------------------------------------------------

export interface ChatThreadSummary {
  id: string
  title: string
  lastMessageAt: string
  createdAt: string
  archived: boolean
}

// -- Messages ----------------------------------------------------------------

export type ChatRole = 'user' | 'assistant' | 'system'

export type VizTool =
  | 'kpi'
  | 'line'
  | 'area'
  | 'bar'
  | 'stacked_bar'
  | 'radar'
  | 'gauge'
  | 'pie'
  | 'donut'
  | 'mermaid'
  | 'table'
  | 'map'

export type MessagePayload =
  | { kind: 'viz'; tool: VizTool; data: unknown }
  | { kind: 'sheet_result'; sheetId: string; selection: unknown }
  | { kind: 'error'; code: ChatErrorCode; message: string; retryOf: string }

// -- F56 — Sources de message (FR-011) ----------------------------------

export type SourceVerificationStatus = 'verified' | 'outdated'

export interface SourceRef {
  source_id: string
  title: string
  publisher: string
  url: string
  page?: string | null
  section?: string | null
  verification_status: SourceVerificationStatus
  version?: string | null
  citation_index: number
  spans?: Array<[number, number]>
}

export interface UnsourcedClaim {
  thread_id: string | null
  message_id: string | null
  agent_run_id: string | null
  claim: string
  reason: string
  span: [number, number] | null
  unsourced_flag_id: string | null
  auto: boolean
}

export interface ChatMessage {
  id: string
  threadId: string
  role: ChatRole
  content: string
  payload: MessagePayload | null
  createdAt: string
  sequenceId?: number
  streaming?: boolean
  hasMutation?: boolean
  // F56 — sources citées agrégées dans ce message
  sources?: SourceRef[]
  // F56 — claims non sourcés signalés sur ce message
  unsourcedClaims?: UnsourcedClaim[]
}

// -- Streaming ---------------------------------------------------------------

export type StreamingPhase =
  | 'idle'
  | 'streaming'
  | 'awaiting_sheet'
  | 'error'
  | 'cancelled'

export interface StreamingState {
  threadId: string
  userMessageId: string
  assistantMessageId: string
  abortController: AbortController
  seqSeen: Set<number>
  partialContent: string
  startedAt: number
  firstTokenAt: number | null
  retryCount: number
  phase: StreamingPhase
}

// -- Errors ------------------------------------------------------------------

export type ChatErrorCode =
  | 'validation'
  | 'timeout'
  | 'network'
  | 'forbidden'
  | 'unknown'

export interface ChatError {
  messageId: string
  retryOf: { content: string; payload: unknown | null }
  code: ChatErrorCode
  message: string
}

// -- Event bus ---------------------------------------------------------------

export type EventBusEventType =
  | 'entity_updated'
  | 'entity_created'
  | 'entity_deleted'
  | 'memory_updated'

export type EventBusSource = 'llm' | 'manual' | 'import' | 'admin'

export interface EventBusEvent {
  eventType: EventBusEventType
  entityType: string
  entityId: string
  fieldsUpdated?: string[]
  source: EventBusSource
  ts: string
}

// -- Memory snapshot ---------------------------------------------------------

export interface MemoryEntry {
  kind: string
  preview: string
  entityRef?: string
}

export interface MemorySnapshot {
  threadId: string
  size: number
  entries: MemoryEntry[]
  fetchedAt: string
}

// -- SSE frames (parsed from POST /me/chat/threads/{id}/messages) -----------

export type StreamFrame =
  | { event: 'token'; id?: number; data: { content: string; assistantMessageId?: string } }
  | {
      event: 'message_done'
      id?: number
      data: {
        messageId: string
        payload?: MessagePayload | null
        content?: string
        // F56 — sources citées dans ce message (FR-011)
        sources?: SourceRef[]
        // F56 — état de validation sourçage du run agent
        sourcing_status?: 'ok' | 'retried_ok' | 'failed' | null
        // F56 — true si fallback sourçage a tronqué/substitué
        degraded?: boolean
      }
    }
  | { event: 'tool_invoke'; id?: number; data: unknown }
  | { event: 'mutation'; id?: number; data: Omit<EventBusEvent, 'source'> & { source?: EventBusSource } }
  | { event: 'error'; id?: number; data: { code: ChatErrorCode; message: string } }
  | { event: 'memory_updated'; id?: number; data: { threadId: string; size?: number } }
  // F56 — claim non sourcé signalé (flag_unsourced ou auto-rollup permissif)
  | { event: 'unsourced_claim'; id?: number; data: UnsourcedClaim }

// -- Send payload ------------------------------------------------------------

export interface SendMessageBody {
  content: string
  // Backend (PostMessageBody) exige context_json (extra='forbid', whitelist
  // page/entity_type/entity_id/selection). On envoie toujours un objet.
  context_json: Record<string, unknown>
  payload_json?: Record<string, unknown> | null
}
