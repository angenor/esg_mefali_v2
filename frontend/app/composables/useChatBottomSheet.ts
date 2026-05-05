/**
 * useChatBottomSheet — API publique de l'orchestrateur F39.
 *
 * Contrat : specs/039-bottom-sheet-engine/contracts/orchestrator-events.md.
 *  - un seul `current` à la fois (FR-002)
 *  - `open()` rejette si déjà ouvert
 *  - `rebuildFromThread()` lit le dernier message tool pending via API existante (F14)
 *  - `close('freetext'|'cancel')` émet l'event DOM `dismiss-for-freetext`
 */
import { computed, type ComputedRef, type Ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useChatBottomSheetStore, type CloseReason } from '~/stores/chatBottomSheet'
import { toolInstructionSchema, type ToolInstruction } from '~/types/tools/contracts'

export interface UseChatBottomSheet {
  current: Readonly<Ref<ToolInstruction | null>>
  isOpen: ComputedRef<boolean>
  open(instruction: unknown): Promise<void>
  close(reason: CloseReason): Promise<void>
  rebuildFromThread(threadId: string): Promise<void>
}

const FREETEXT_EVENT = 'chat:bottom-sheet:dismiss-for-freetext'

function dispatchFreeText(detail: { tool: string; message_id: string }): void {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(FREETEXT_EVENT, { detail }))
}

interface RebuildOptions {
  /** Override pour les tests : retourne directement le message pending. */
  fetchPending?: (threadId: string) => Promise<unknown>
}

const apiBaseFromRuntime = (): string => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const cfg = (globalThis as any).useRuntimeConfig?.()
  return String(cfg?.public?.apiBase ?? 'http://localhost:8010').replace(/\/$/, '')
}

async function defaultFetchPending(threadId: string): Promise<unknown> {
  const url = `${apiBaseFromRuntime()}/me/chat/threads/${threadId}/pending-tool`
  const res = await fetch(url, { credentials: 'include', headers: { accept: 'application/json' } })
  if (res.status === 204 || res.status === 404) return null
  if (!res.ok) throw new Error(`pending-tool HTTP ${res.status}`)
  return res.json()
}

export function useChatBottomSheet(options: RebuildOptions = {}): UseChatBottomSheet {
  const store = useChatBottomSheetStore()
  const { current } = storeToRefs(store)

  async function open(raw: unknown): Promise<void> {
    if (store.isOpen) {
      // FR-002 : un seul sheet à la fois.
      // eslint-disable-next-line no-console
      console.warn('[useChatBottomSheet] open ignoré : un sheet est déjà ouvert')
      return
    }
    const result = toolInstructionSchema.safeParse(raw)
    if (!result.success) {
      // eslint-disable-next-line no-console
      console.warn('[useChatBottomSheet] payload invalide, ignoré', result.error.issues)
      return
    }
    store.setCurrent(result.data as ToolInstruction)
  }

  async function close(reason: CloseReason): Promise<void> {
    const inst = store.current
    if (!inst) return
    store.markClosing(true)
    if (reason === 'freetext' || reason === 'cancel') {
      store.requestFreeText()
      dispatchFreeText({ tool: inst.tool, message_id: inst.context.message_id })
    }
    store.reset()
  }

  async function rebuildFromThread(threadId: string): Promise<void> {
    const fetcher = options.fetchPending ?? defaultFetchPending
    try {
      const pending = await fetcher(threadId)
      if (!pending) return
      await open(pending)
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('[useChatBottomSheet] rebuildFromThread a échoué', err)
    }
  }

  return {
    current: current as Readonly<Ref<ToolInstruction | null>>,
    isOpen: computed(() => store.isOpen),
    open,
    close,
    rebuildFromThread,
  }
}

export const FREETEXT_EVENT_NAME = FREETEXT_EVENT
