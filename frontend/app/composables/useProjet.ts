// F43 T039 — useProjet(id) : autosave debounced + version + conflict + fetch détail.
//
// Symétrique à useEntrepriseProfile, scopé à un projet précis.
import { computed, onScopeDispose, type ComputedRef } from "vue"
import { useProjetsStore, type ProjetRead, type DocumentProjetRead } from "~/stores/projets"
import type { ConflictBlock } from "~/stores/entreprise"
import { useToast } from "~/composables/useToast"
import { useChatEventBus } from "~/composables/useChatEventBus"
import type { EventBusEvent } from "~/types/chat"

const DEBOUNCE_MS = 800

interface PendingFlush {
  timer: ReturnType<typeof setTimeout> | null
  attempt: number
}

const flushers = new Map<string, PendingFlush>()
function key(id: string, field: string): string {
  return `${id}::${field}`
}

export interface UseProjet {
  data: ComputedRef<ProjetRead | null>
  documents: ComputedRef<DocumentProjetRead[]>
  saving: ComputedRef<Record<string, boolean>>
  errors: ComputedRef<Record<string, string | null>>
  conflict: ComputedRef<ConflictBlock | null>
  patchField: (field: string, value: unknown) => void
  flushNow: (field?: string) => Promise<void>
  resolveConflict: (choice: "mine" | "theirs" | "cancel") => Promise<void>
  load: () => Promise<void>
  softDelete: () => Promise<boolean>
}

export interface UseProjetOptions {
  debounceMs?: number
}

export function useProjet(id: string, options: UseProjetOptions = {}): UseProjet {
  const store = useProjetsStore()
  const toast = useToast()
  const bus = useChatEventBus()
  const debounceMs = options.debounceMs ?? DEBOUNCE_MS

  // T053 — souscription EventBus chat ↔ projet (filtrage par entityId).
  function onEntityUpdated(event: EventBusEvent): void {
    if (event.entityType !== "projet" || event.entityId !== id) return
    const fields = event.fieldsUpdated ?? []
    const pendingForId = Array.from(flushers.keys()).filter((k) => k.startsWith(`${id}::`))
    const pendingFields = pendingForId.map((k) => k.slice(id.length + 2))
    const overlap = fields.filter((f) => pendingFields.includes(f))
    void (async () => {
      try {
        await store.loadOne(id)
        if (overlap.length === 0) {
          toast.push({ severity: "info", message: "Mis à jour par le chat", duration: 2000 })
        } else {
          const field = overlap[0]!
          const current = (store.byId[id] as unknown as Record<string, unknown>)?.[field] ?? null
          store.setConflict(id, {
            field,
            your: null,
            current,
            current_version: store.versionById[id] ?? 0,
          })
        }
      } catch {
        /* silencieux */
      }
    })()
  }
  const off = bus.on("entity_updated", onEntityUpdated, { ignoreLlmSource: false })
  onScopeDispose(() => off())

  function patchField(field: string, value: unknown): void {
    const k = key(id, field)
    const existing = flushers.get(k)
    if (existing?.timer) clearTimeout(existing.timer)
    const entry: PendingFlush = { timer: null, attempt: 0 }
    entry.timer = setTimeout(() => {
      void executeFlush(field, value, entry)
    }, debounceMs)
    flushers.set(k, entry)
  }

  async function executeFlush(field: string, value: unknown, entry: PendingFlush): Promise<void> {
    const result = await store.patchField(id, field, value)
    if (result.ok) {
      flushers.delete(key(id, field))
      toast.push({ severity: "success", message: "Enregistré", duration: 1500 })
      return
    }
    if (result.error === "conflict" || result.error === "validation") {
      flushers.delete(key(id, field))
      return
    }
    // network → backoff
    const next = entry.attempt
    const delays = [250, 500, 1000, 2000, 4000]
    if (next < delays.length) {
      entry.attempt += 1
      entry.timer = setTimeout(() => void executeFlush(field, value, entry), delays[next])
    } else {
      toast.push({
        severity: "error",
        message: "Modifications non sauvegardées",
        duration: 0,
      })
      flushers.delete(key(id, field))
    }
  }

  async function flushNow(field?: string): Promise<void> {
    const targets = field ? [key(id, field)] : Array.from(flushers.keys()).filter((k) => k.startsWith(`${id}::`))
    for (const k of targets) {
      const entry = flushers.get(k)
      if (!entry) continue
      if (entry.timer) {
        clearTimeout(entry.timer)
        entry.timer = null
      }
    }
  }

  async function resolveConflict(choice: "mine" | "theirs" | "cancel"): Promise<void> {
    const conflict = store.conflicts[id]
    if (!conflict) return
    if (choice === "cancel") {
      store.setConflict(id, null)
      return
    }
    if (choice === "theirs") {
      store.versionById = { ...store.versionById, [id]: conflict.current_version }
      store.setConflict(id, null)
      return
    }
    store.versionById = { ...store.versionById, [id]: conflict.current_version }
    store.setConflict(id, null)
    const entry: PendingFlush = { timer: null, attempt: 0 }
    flushers.set(key(id, conflict.field), entry)
    await executeFlush(conflict.field, conflict.your, entry)
  }

  async function load(): Promise<void> {
    await store.loadOne(id)
  }

  async function softDelete(): Promise<boolean> {
    return await store.softDelete(id)
  }

  return {
    data: computed(() => store.byId[id] ?? null),
    documents: computed(() => store.documentsById[id] ?? []),
    saving: computed(() => store.saving[id] ?? {}),
    errors: computed(() => store.errors[id] ?? {}),
    conflict: computed(() => store.conflicts[id] ?? null),
    patchField,
    flushNow,
    resolveConflict,
    load,
    softDelete,
  }
}

/** Reset interne — tests uniquement. */
export function __resetProjetFlushers(): void {
  for (const entry of flushers.values()) {
    if (entry.timer) clearTimeout(entry.timer)
  }
  flushers.clear()
}
