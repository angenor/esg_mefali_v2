// F50 T014 — EventBus typé pour les mutations documents (P8 sync).
//
// Émetteur cross-feature : permet au store F50, au chat F41 et à la grille
// projet F43 de rester synchrones sans accès direct au store.

import type { DocumentDetail } from "~/types/documents"

export interface DocumentsEventMap {
  "documents:created": { document: DocumentDetail }
  "documents:status-changed": { documentId: string; ocrStatus: string }
  "documents:validated": { document: DocumentDetail }
  "documents:deleted": { documentId: string }
  "documents:linked-projet": { documentId: string; projetId: string }
  "documents:unlinked-projet": { documentId: string; projetId: string }
}

type Listener<E extends keyof DocumentsEventMap> = (
  payload: DocumentsEventMap[E],
) => void

const listeners = new Map<keyof DocumentsEventMap, Set<Listener<never>>>()

let broadcastChannel: BroadcastChannel | null = null

function getBroadcastChannel(): BroadcastChannel | null {
  if (typeof BroadcastChannel === "undefined") return null
  if (broadcastChannel) return broadcastChannel
  broadcastChannel = new BroadcastChannel("documents")
  broadcastChannel.onmessage = (ev: MessageEvent) => {
    const data = ev.data as { type?: keyof DocumentsEventMap; payload?: unknown }
    if (data?.type) {
      dispatchLocal(data.type, data.payload as DocumentsEventMap[keyof DocumentsEventMap])
    }
  }
  return broadcastChannel
}

function dispatchLocal<E extends keyof DocumentsEventMap>(
  event: E,
  payload: DocumentsEventMap[E],
): void {
  const set = listeners.get(event)
  if (!set) return
  for (const fn of set) {
    try {
      ;(fn as Listener<E>)(payload)
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error("[documentEvents] listener error", e)
    }
  }
}

export function emit<E extends keyof DocumentsEventMap>(
  event: E,
  payload: DocumentsEventMap[E],
): void {
  dispatchLocal(event, payload)
  const ch = getBroadcastChannel()
  ch?.postMessage({ type: event, payload })
}

export function on<E extends keyof DocumentsEventMap>(
  event: E,
  listener: Listener<E>,
): () => void {
  let set = listeners.get(event)
  if (!set) {
    set = new Set()
    listeners.set(event, set)
  }
  set.add(listener as Listener<never>)
  // Initialise le BroadcastChannel pour recevoir les events cross-onglet.
  getBroadcastChannel()
  return () => off(event, listener)
}

export function off<E extends keyof DocumentsEventMap>(
  event: E,
  listener: Listener<E>,
): void {
  const set = listeners.get(event)
  if (!set) return
  set.delete(listener as Listener<never>)
}

export const documentEvents = { emit, on, off }
