// F51 T029 — Sync URL ↔ store des filtres matching (FR-002 spec).
//
// Persistance bidirectionnelle : query string ↔ store Pinia. `replace:true`
// pour ne pas polluer history.

import { watch, onMounted } from "vue"
import type { MatchingFilters, OffreType } from "~/types/matching"
import { useMatchingStore } from "~/stores/matching"

const VALID_TYPES: OffreType[] = ["credit", "subvention", "garantie", "autre"]

function parseQuery(query: Record<string, unknown>): MatchingFilters {
  const f: MatchingFilters = {}
  const t = String(query.type ?? "")
  if (VALID_TYPES.includes(t as OffreType)) f.type = t as OffreType
  // Accepte les deux formes : `montant_min_eur` (canonique API) et `montant_min`
  // (canonique URL F51, ex. CTA simulateur → /matching?montant_max=X&duree_max=Y).
  const mn = Number.parseInt(
    String(query.montant_min_eur ?? query.montant_min ?? ""),
    10,
  )
  if (!Number.isNaN(mn) && mn >= 0) f.montant_min_eur = mn
  const mx = Number.parseInt(
    String(query.montant_max_eur ?? query.montant_max ?? ""),
    10,
  )
  if (!Number.isNaN(mx) && mx >= 0) f.montant_max_eur = mx
  const dmn = Number.parseInt(
    String(query.duree_min_mois ?? query.duree_min ?? ""),
    10,
  )
  if (!Number.isNaN(dmn) && dmn > 0) f.duree_min_mois = dmn
  const dmx = Number.parseInt(
    String(query.duree_max_mois ?? query.duree_max ?? ""),
    10,
  )
  if (!Number.isNaN(dmx) && dmx > 0) f.duree_max_mois = dmx
  const ii = String(query.intermediaire_id ?? "").trim()
  if (ii) f.intermediaire_id = ii
  const sec = String(query.secteur ?? "").trim().toLowerCase()
  if (sec) f.secteur = sec
  const q = String(query.q ?? "").trim()
  if (q) f.q = q
  return f
}

function toQuery(filters: MatchingFilters): Record<string, string> {
  const out: Record<string, string> = {}
  for (const [k, v] of Object.entries(filters)) {
    if (v === undefined || v === null || v === "") continue
    out[k] = String(v)
  }
  return out
}

function shallowEqual(
  a: Record<string, string>,
  b: Record<string, string>,
): boolean {
  const ka = Object.keys(a)
  const kb = Object.keys(b)
  if (ka.length !== kb.length) return false
  for (const k of ka) if (a[k] !== b[k]) return false
  return true
}

export interface UseMatchingFiltersApi {
  hydrateFromQuery(query: Record<string, unknown>): void
  syncToQuery(): void
}

export function useMatchingFilters(): UseMatchingFiltersApi {
  const store = useMatchingStore()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const g = globalThis as any

  function hydrateFromQuery(query: Record<string, unknown>): void {
    store.setFilters(parseQuery(query))
  }

  async function syncToQuery(): Promise<void> {
    const route = g.useRoute?.()
    const navigateTo = g.navigateTo as
      | ((to: { query: Record<string, string> }, opts?: { replace?: boolean }) => Promise<void>)
      | undefined
    if (!route || !navigateTo) return
    const next = toQuery(store.filters)
    const current: Record<string, string> = {}
    for (const [k, v] of Object.entries(route.query ?? {})) {
      if (v !== null && v !== undefined) current[k] = String(v)
    }
    if (shallowEqual(next, current)) return
    await navigateTo({ query: next }, { replace: true })
  }

  onMounted(() => {
    const route = g.useRoute?.()
    if (route?.query) hydrateFromQuery(route.query)
  })

  watch(
    () => store.filters,
    () => {
      void syncToQuery()
    },
    { deep: true },
  )

  return { hydrateFromQuery, syncToQuery }
}

// Exports utilitaires (testables sans Nuxt runtime).
export { parseQuery, toQuery, shallowEqual }
