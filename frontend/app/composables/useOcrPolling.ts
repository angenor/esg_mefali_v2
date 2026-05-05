// F50 T011 — Polling OCR (2 s → backoff 3,4,5 s, plafond 60 s).
//
// Cf. specs/050-documents-ocr-ui/research.md §2 :
//   - intervalle initial 2 s, puis 3, 4, 5 s, plafonné à 5 s.
//   - durée totale plafonnée à 60 s ; au-delà, statut UI "timeout".
//   - cancel automatique sur états terminaux ou unmount.

import type { DocumentDetail } from "~/types/documents"

const INTERVALS_MS = [2000, 3000, 4000, 5000]
const MAX_TOTAL_MS = 60_000

type Fetcher = (docId: string) => Promise<DocumentDetail>

export interface OcrPollingHandlers {
  onUpdate: (doc: DocumentDetail) => void
  onTimeout?: (docId: string) => void
  onError?: (docId: string, err: unknown) => void
}

export interface OcrPollingHandle {
  stop: () => void
  isActive: () => boolean
}

function isTerminal(status: string): boolean {
  return status === "done" || status === "error" || status === "failed"
}

export function useOcrPolling(fetcher: Fetcher) {
  function start(docId: string, handlers: OcrPollingHandlers): OcrPollingHandle {
    let stopped = false
    let timer: ReturnType<typeof setTimeout> | null = null
    let attempt = 0
    const startedAt = Date.now()

    const tick = async () => {
      if (stopped) return
      try {
        const doc = await fetcher(docId)
        if (stopped) return
        handlers.onUpdate(doc)
        if (isTerminal(doc.ocr_status)) {
          stopped = true
          return
        }
      } catch (err) {
        handlers.onError?.(docId, err)
      }
      const elapsed = Date.now() - startedAt
      if (elapsed >= MAX_TOTAL_MS) {
        stopped = true
        handlers.onTimeout?.(docId)
        return
      }
      const delay = INTERVALS_MS[Math.min(attempt, INTERVALS_MS.length - 1)]!
      attempt++
      timer = setTimeout(tick, delay)
    }

    timer = setTimeout(tick, INTERVALS_MS[0])

    return {
      stop: () => {
        stopped = true
        if (timer) clearTimeout(timer)
      },
      isActive: () => !stopped,
    }
  }

  return { start }
}
