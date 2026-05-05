// F51 T012 — EventBus typé pour les mutations candidature/wizard/simulateur.
//
// Permet au store F51, au chat F41 et au composant `<ChatBottomSheet>` de
// rester synchrones sans coupling direct (P8 — édition manuelle invalide
// le contexte LLM en temps réel).
//
// Pattern miroir de `documentEvents.ts` (F50 T014).

import mitt from "mitt"

export type CandidatureEventMap = {
  "candidature:updated": { candidature_id: string; version: number }
  "wizard:step:changed": {
    candidature_id: string
    from: number
    to: number
  }
  "wizard:document:linked": {
    candidature_id: string
    document_id: string
    checklist_key: string
  }
  "wizard:document:unlinked": {
    candidature_id: string
    document_id: string
    checklist_key: string
  }
  "simulateur:saved": { simulation_id: string; label: string }
}

const emitter = mitt<CandidatureEventMap>()

export function emitCandidatureEvent<E extends keyof CandidatureEventMap>(
  event: E,
  payload: CandidatureEventMap[E],
): void {
  emitter.emit(event, payload as never)
}

export function onCandidatureEvent<E extends keyof CandidatureEventMap>(
  event: E,
  handler: (payload: CandidatureEventMap[E]) => void,
): () => void {
  emitter.on(event, handler as never)
  return () => emitter.off(event, handler as never)
}

export function clearCandidatureEvents(): void {
  emitter.all.clear()
}
