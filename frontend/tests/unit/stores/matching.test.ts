// F51 T013 — Store matching : initial state.

import { setActivePinia, createPinia } from "pinia"
import { beforeEach, describe, expect, it } from "vitest"
import { useMatchingStore } from "~/stores/matching"

describe("useMatchingStore", () => {
  beforeEach(() => setActivePinia(createPinia()))

  it("has clean initial state", () => {
    const s = useMatchingStore()
    expect(s.projetActifId).toBeNull()
    expect(s.filters).toEqual({})
    expect(s.offres).toEqual([])
    expect(s.loading).toBe(false)
    expect(s.error).toBeNull()
    expect(s.carteVisible).toBe(false)
    expect(s.drawerOffreId).toBeNull()
    expect(s.hasResults).toBe(false)
    expect(s.isScoredMode).toBe(false)
  })

  it("setProjetActif switches to scored mode", () => {
    const s = useMatchingStore()
    s.setProjetActif("p-1")
    expect(s.isScoredMode).toBe(true)
  })

  it("setFilters replaces filters object", () => {
    const s = useMatchingStore()
    s.setFilters({ type: "subvention", montant_max_eur: 100000 })
    expect(s.filters.type).toBe("subvention")
    expect(s.filters.montant_max_eur).toBe(100000)
  })
})
