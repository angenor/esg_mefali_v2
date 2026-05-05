// F51 T030 — Comparateur d'offres (max 3, persistance localStorage).
//
// Cf. research.md §4.

import { ref, computed, onMounted, onUnmounted } from "vue"
import type { ComputedRef, Ref } from "vue"
import type { ComparatorEntry, OffreMatchItem } from "~/types/matching"

const LS_KEY = "mefali:matching:comparator:v1"
export const COMPARATOR_MAX = 3

function readStorage(): ComparatorEntry[] {
  if (typeof window === "undefined") return []
  try {
    const raw = window.localStorage.getItem(LS_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return []
    return parsed.filter(
      (e): e is ComparatorEntry =>
        typeof e === "object" && e !== null && "offre_id" in e,
    )
  } catch {
    return []
  }
}

function writeStorage(entries: ComparatorEntry[]): void {
  if (typeof window === "undefined") return
  try {
    window.localStorage.setItem(LS_KEY, JSON.stringify(entries))
  } catch {
    // localStorage plein / désactivé : silencieux
  }
}

export interface UseComparateurApi {
  entries: Ref<ComparatorEntry[]>
  count: ComputedRef<number>
  has: (offreId: string) => boolean
  add: (offre: OffreMatchItem, projetId: string | null) => boolean
  remove: (offreId: string) => void
  clear: () => void
  syncFromStorage: () => void
}

export function useComparateur(): UseComparateurApi {
  const entries = ref<ComparatorEntry[]>(readStorage())
  const count = computed(() => entries.value.length)

  function has(offreId: string): boolean {
    return entries.value.some((e) => e.offre_id === offreId)
  }

  function add(offre: OffreMatchItem, projetId: string | null): boolean {
    if (has(offre.offre_id)) return true
    if (entries.value.length >= COMPARATOR_MAX) return false
    const entry: ComparatorEntry = {
      offre_id: offre.offre_id,
      projet_id: projetId,
      snapshot_label: offre.nom,
      snapshot_montant: offre.montant_max,
      snapshot_intermediaire: offre.intermediaire.nom,
      added_at: new Date().toISOString(),
    }
    entries.value = [...entries.value, entry]
    writeStorage(entries.value)
    return true
  }

  function remove(offreId: string): void {
    entries.value = entries.value.filter((e) => e.offre_id !== offreId)
    writeStorage(entries.value)
  }

  function clear(): void {
    entries.value = []
    writeStorage([])
  }

  function syncFromStorage(): void {
    entries.value = readStorage()
  }

  function onStorage(ev: StorageEvent): void {
    if (ev.key === LS_KEY) syncFromStorage()
  }

  onMounted(() => {
    if (typeof window !== "undefined") {
      window.addEventListener("storage", onStorage)
    }
  })
  onUnmounted(() => {
    if (typeof window !== "undefined") {
      window.removeEventListener("storage", onStorage)
    }
  })

  return { entries, count, has, add, remove, clear, syncFromStorage }
}
