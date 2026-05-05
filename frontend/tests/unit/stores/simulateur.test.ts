// F51 T015 — Store simulateur : initial state.

import { setActivePinia, createPinia } from "pinia"
import { beforeEach, describe, expect, it } from "vitest"
import { useSimulateurStore } from "~/stores/simulateur"

describe("useSimulateurStore", () => {
  beforeEach(() => setActivePinia(createPinia()))

  it("has default inputs (EUR 100k / 60 mois / solaire)", () => {
    const s = useSimulateurStore()
    expect(s.inputs.montant.amount).toBe("100000")
    expect(s.inputs.montant.currency).toBe("EUR")
    expect(s.inputs.duree_mois).toBe(60)
    expect(s.inputs.type_investissement).toBe("renouvelable_solaire")
    expect(s.inputs.part_subvention_pct).toBe(0)
    expect(s.results).toBeNull()
    expect(s.computing).toBe(false)
    expect(s.history).toEqual([])
  })

  it("setInput updates immutably", () => {
    const s = useSimulateurStore()
    const prev = s.inputs
    s.setInput("duree_mois", 84)
    expect(s.inputs).not.toBe(prev) // new object
    expect(s.inputs.duree_mois).toBe(84)
  })

  it("rehydrateFromQuery accepts montant + duree", () => {
    const s = useSimulateurStore()
    s.rehydrateFromQuery({ montant: "250000", duree: "84", currency: "EUR" })
    expect(s.inputs.montant.amount).toBe("250000")
    expect(s.inputs.duree_mois).toBe(84)
  })
})
