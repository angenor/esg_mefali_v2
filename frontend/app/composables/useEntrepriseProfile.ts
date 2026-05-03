// F43 T019 — useEntrepriseProfile : autosave debounced 800 ms + version + conflict.
//
// Pipeline d'écriture :
//   patchField(field, value)
//     → enfile dans pendingChanges
//     → debounce 800 ms (par champ, AbortController dédié)
//     → PATCH /me/entreprise { [field]: value, version }
//     → 200 : applique data + version + completion ; toast "Enregistré"
//     → 409 : ouvre ConflictDialog (set conflict)
//     → 422 : set errors[field]
//     → 5xx : retry exponentiel 250 → 4000 ms ; après n=4 : bannière persistante.
//
// `flushNow()` permet aux tests E2E de forcer le flush sans attendre 800 ms.
import { computed, onScopeDispose, type ComputedRef } from "vue"
import {
  useEntrepriseStore,
  type ConflictBlock,
  type EntrepriseRead,
  type CompletenessOut,
} from "~/stores/entreprise"
import { useToast } from "~/composables/useToast"
import { useChatEventBus } from "~/composables/useChatEventBus"
import type { EventBusEvent } from "~/types/chat"

const DEBOUNCE_MS = 800
const RETRY_DELAYS_MS = [250, 500, 1000, 2000, 4000]

interface PendingFlush {
  timer: ReturnType<typeof setTimeout> | null
  controller: AbortController | null
  attempt: number
}

const flushers = new Map<string, PendingFlush>()

export interface UseEntrepriseProfile {
  data: ComputedRef<EntrepriseRead | null>
  version: ComputedRef<number | null>
  saving: ComputedRef<Record<string, boolean>>
  errors: ComputedRef<Record<string, string | null>>
  conflict: ComputedRef<ConflictBlock | null>
  patchField: (field: string, value: unknown) => void
  flushNow: (field?: string) => Promise<void>
  resolveConflict: (choice: "mine" | "theirs" | "cancel") => Promise<void>
}

interface ApiClient {
  patch(field: string, value: unknown, version: number, signal: AbortSignal): Promise<EntrepriseRead>
  completeness(): Promise<CompletenessOut>
}

function defaultClient(): ApiClient {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase as string
  return {
    patch(field, value, version, signal) {
      return $fetch<EntrepriseRead>(`${apiBase}/me/entreprise`, {
        method: "PATCH",
        credentials: "include",
        body: { [field]: value, version },
        signal,
      })
    },
    completeness() {
      return $fetch<CompletenessOut>(`${apiBase}/me/entreprise/completeness`, {
        credentials: "include",
      })
    },
  }
}

export interface UseEntrepriseProfileOptions {
  client?: ApiClient
  /** Délai de debounce (par défaut 800 ms ; testable). */
  debounceMs?: number
  /** Backoff (testable). */
  retryDelays?: number[]
}

export function useEntrepriseProfile(
  options: UseEntrepriseProfileOptions = {},
): UseEntrepriseProfile {
  const store = useEntrepriseStore()
  const toast = useToast()
  const bus = useChatEventBus()
  const client = options.client ?? defaultClient()
  const debounceMs = options.debounceMs ?? DEBOUNCE_MS
  const retryDelays = options.retryDelays ?? RETRY_DELAYS_MS

  // T052 — souscription EventBus chat ↔ profil entreprise.
  function onEntityUpdated(event: EventBusEvent): void {
    if (event.entityType !== "entreprise") return
    const fields = event.fieldsUpdated ?? []
    const localPending = fields.filter((f) => store.pendingChanges[f] !== undefined)
    if (localPending.length === 0) {
      // Pas de chevauchement → re-fetch + flash.
      void (async () => {
        try {
          const updated = await $fetch<EntrepriseRead>(
            `${(useRuntimeConfig().public.apiBase as string)}/me/entreprise`,
            { credentials: "include" },
          )
          store.applyData(updated)
          toast.push({
            severity: "info",
            message: "Mis à jour par le chat",
            duration: 2000,
          })
        } catch {
          /* silencieux */
        }
      })()
      return
    }
    // Chevauchement → re-fetch puis ouvre ConflictDialog sur le premier champ contesté.
    void (async () => {
      try {
        const updated = await $fetch<EntrepriseRead>(
          `${(useRuntimeConfig().public.apiBase as string)}/me/entreprise`,
          { credentials: "include" },
        )
        const field = localPending[0]!
        store.setConflict({
          field,
          your: store.pendingChanges[field],
          current: (updated as Record<string, unknown>)[field] ?? null,
          current_version: updated.version,
        })
      } catch {
        /* silencieux */
      }
    })()
  }
  const off = bus.on("entity_updated", onEntityUpdated, { ignoreLlmSource: false })
  onScopeDispose(() => off())

  function patchField(field: string, value: unknown): void {
    store.setPendingChange(field, value)
    store.setError(field, null)
    const existing = flushers.get(field)
    if (existing?.timer) clearTimeout(existing.timer)
    if (existing?.controller) existing.controller.abort()
    const entry: PendingFlush = { timer: null, controller: null, attempt: 0 }
    entry.timer = setTimeout(() => {
      void executeFlush(field, value, entry)
    }, debounceMs)
    flushers.set(field, entry)
  }

  async function executeFlush(field: string, value: unknown, entry: PendingFlush): Promise<void> {
    if (store.version == null) {
      store.setError(field, "no_version")
      return
    }
    entry.controller = new AbortController()
    store.setSaving(field, true)
    try {
      const updated = await client.patch(field, value, store.version, entry.controller.signal)
      store.applyData(updated)
      store.clearPendingChange(field)
      store.setError(field, null)
      store.setConflict(null)
      // Recharge la complétude (tolérance erreur — n'efface pas la valeur courante).
      try {
        const completeness = await client.completeness()
        store.applyCompletion(completeness)
      } catch {
        /* silencieux */
      }
      toast.push({
        severity: "success",
        message: "Enregistré",
        duration: 2000,
      })
      flushers.delete(field)
    } catch (err: unknown) {
      const aborted =
        (err as { name?: string })?.name === "AbortError" ||
        entry.controller?.signal.aborted
      if (aborted) return
      const status =
        (err as { statusCode?: number; status?: number })?.statusCode ??
        (err as { status?: number })?.status
      if (status === 409) {
        const data = (err as { data?: { current_version: number; [key: string]: unknown } }).data
        store.setConflict({
          field,
          your: value,
          current: data?.[field] ?? null,
          current_version: data?.current_version ?? store.version ?? 0,
        })
        flushers.delete(field)
        return
      }
      if (status === 422) {
        const detail = (err as { data?: { detail?: unknown } }).data?.detail
        const message = Array.isArray(detail)
          ? String((detail[0] as { msg?: string })?.msg ?? "validation")
          : "validation"
        store.setError(field, message)
        flushers.delete(field)
        return
      }
      // 5xx ou réseau : retry exponentiel.
      const next = entry.attempt
      if (next < retryDelays.length) {
        entry.attempt += 1
        const delay = retryDelays[next] ?? 4000
        entry.timer = setTimeout(() => void executeFlush(field, value, entry), delay)
      } else {
        store.setError(field, "network")
        toast.push({
          severity: "error",
          message: "Modifications non sauvegardées",
          duration: 0,
          actionLabel: "Réessayer",
          onAction: () => {
            entry.attempt = 0
            void executeFlush(field, value, entry)
          },
        })
      }
    } finally {
      store.setSaving(field, false)
    }
  }

  async function flushNow(field?: string): Promise<void> {
    const fields = field ? [field] : Array.from(flushers.keys())
    for (const f of fields) {
      const entry = flushers.get(f)
      if (!entry) continue
      if (entry.timer) {
        clearTimeout(entry.timer)
        entry.timer = null
      }
      const value = store.pendingChanges[f]
      if (value === undefined) continue
      // eslint-disable-next-line no-await-in-loop
      await executeFlush(f, value, entry)
    }
  }

  async function resolveConflict(choice: "mine" | "theirs" | "cancel"): Promise<void> {
    const conflict = store.conflict
    if (!conflict) return
    if (choice === "cancel") {
      store.setConflict(null)
      return
    }
    if (choice === "theirs") {
      // Bumper la version locale et abandonner notre patch.
      store.version = conflict.current_version
      store.clearPendingChange(conflict.field)
      store.setConflict(null)
      return
    }
    // 'mine' → re-tenter le PATCH avec la version courante du serveur.
    store.version = conflict.current_version
    store.setConflict(null)
    const entry: PendingFlush = { timer: null, controller: null, attempt: 0 }
    flushers.set(conflict.field, entry)
    await executeFlush(conflict.field, conflict.your, entry)
  }

  return {
    data: computed(() => store.data),
    version: computed(() => store.version),
    saving: computed(() => store.saving),
    errors: computed(() => store.errors),
    conflict: computed(() => store.conflict),
    patchField,
    flushNow,
    resolveConflict,
  }
}

/** Reset interne — tests uniquement. */
export function __resetEntrepriseProfileFlushers(): void {
  for (const entry of flushers.values()) {
    if (entry.timer) clearTimeout(entry.timer)
    if (entry.controller) entry.controller.abort()
  }
  flushers.clear()
}
