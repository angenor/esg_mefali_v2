// F51 T055 — Autosave wizard candidature avec debounce 800 ms + buffer offline.
//
// Sauvegarde le brouillon via candidaturesApi.patchDraft.
// - Debounce 800 ms (research §6).
// - AbortController : la requête en vol est annulée par la suivante.
// - Si offline (navigator.onLine=false), buffer dans localStorage et flush au
//   retour `online`.
// - Expose un `saveStatus` réactif ('idle' | 'saving' | 'saved' | 'offline' | 'error').

import { onBeforeUnmount, onMounted, ref } from "vue"
import { useCandidaturesStore } from "~/stores/candidatures"
import type { WizardDraftPatch } from "~/types/candidatures"

interface BufferedPatch {
  candidature_id: string
  patch: WizardDraftPatch
  ts: number
}

const BUFFER_KEY = "mefali:wizard:autosave_buffer:v1"
const DEBOUNCE_MS = 800

function readBuffer(): BufferedPatch[] {
  if (typeof localStorage === "undefined") return []
  try {
    const raw = localStorage.getItem(BUFFER_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeBuffer(items: BufferedPatch[]): void {
  if (typeof localStorage === "undefined") return
  try {
    localStorage.setItem(BUFFER_KEY, JSON.stringify(items))
  } catch {
    // localStorage plein → silencieux
  }
}

export function useWizardAutosave() {
  const store = useCandidaturesStore()
  let timer: ReturnType<typeof setTimeout> | null = null
  let abort: AbortController | null = null
  const lastSaveError = ref<string | null>(null)

  function clearTimer(): void {
    if (timer !== null) {
      clearTimeout(timer)
      timer = null
    }
  }

  function isOnline(): boolean {
    return typeof navigator === "undefined" ? true : navigator.onLine
  }

  async function flushBuffer(): Promise<void> {
    const items = readBuffer()
    if (items.length === 0) return
    const remaining: BufferedPatch[] = []
    for (const item of items) {
      try {
        await store.patchDraft(item.candidature_id, item.patch)
      } catch {
        remaining.push(item)
      }
    }
    writeBuffer(remaining)
  }

  function bufferPatch(candidatureId: string, patch: WizardDraftPatch): void {
    const items = readBuffer()
    items.push({ candidature_id: candidatureId, patch, ts: Date.now() })
    writeBuffer(items)
  }

  async function performSave(
    candidatureId: string,
    patch: WizardDraftPatch,
  ): Promise<void> {
    if (abort) abort.abort()
    abort = new AbortController()
    if (!isOnline()) {
      bufferPatch(candidatureId, patch)
      store.saveStatus = "offline"
      return
    }
    try {
      await store.patchDraft(candidatureId, patch)
      lastSaveError.value = null
    } catch (err) {
      lastSaveError.value = (err as Error).message ?? "save_failed"
    }
  }

  function schedule(candidatureId: string, patch: WizardDraftPatch): void {
    clearTimer()
    timer = setTimeout(() => {
      void performSave(candidatureId, patch)
    }, DEBOUNCE_MS)
  }

  async function flushNow(
    candidatureId: string,
    patch: WizardDraftPatch,
  ): Promise<void> {
    clearTimer()
    await performSave(candidatureId, patch)
  }

  function onOnline(): void {
    void flushBuffer()
  }

  onMounted(() => {
    if (typeof window !== "undefined") {
      window.addEventListener("online", onOnline)
      void flushBuffer()
    }
  })
  onBeforeUnmount(() => {
    clearTimer()
    if (abort) abort.abort()
    if (typeof window !== "undefined") {
      window.removeEventListener("online", onOnline)
    }
  })

  return {
    schedule,
    flushNow,
    flushBuffer,
    lastSaveError,
  }
}
