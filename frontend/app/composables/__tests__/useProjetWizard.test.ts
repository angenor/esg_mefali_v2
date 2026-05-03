// F43 T033 — tests useProjetWizard : validation Zod par step + canAdvance + payload submit.
import { beforeEach, describe, expect, it, vi } from "vitest"
import { setActivePinia, createPinia } from "pinia"
import { useProjetWizard } from "../useProjetWizard"
import { useProjetsStore, type ProjetRead } from "~/stores/projets"

describe("useProjetWizard", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it("step 1 invalide tant que nom < 3 caractères", () => {
    const w = useProjetWizard()
    expect(w.canAdvance.value).toBe(false)
    w.data.step1.nom = "ab"
    expect(w.canAdvance.value).toBe(false)
    w.data.step1.nom = "abc"
    expect(w.canAdvance.value).toBe(true)
  })

  it("nom > 120 caractères → erreur nom_max", () => {
    const w = useProjetWizard()
    w.data.step1.nom = "a".repeat(121)
    expect(w.canAdvance.value).toBe(false)
    expect(w.errors.value.nom).toBe("nom_max")
  })

  it("next() bloqué si !canAdvance", () => {
    const w = useProjetWizard()
    expect(w.step.value).toBe(1)
    w.next()
    expect(w.step.value).toBe(1)
    w.data.step1.nom = "Mon projet"
    w.next()
    expect(w.step.value).toBe(2)
  })

  it("step 3 : iso2 doit faire 2 caractères", () => {
    const w = useProjetWizard()
    w.data.step1.nom = "Test"
    w.next()
    w.data.step2.secteur = "energie"
    w.data.step2.type_impact = "mitigation_carbone"
    w.next()
    expect(w.step.value).toBe(3)
    expect(w.canAdvance.value).toBe(false)
    w.data.step3.localisation_pays_iso2 = "BJ"
    w.data.step3.localisation_region = "Atlantique"
    expect(w.canAdvance.value).toBe(true)
  })

  it("submit() délègue à store.create avec payload mappé", async () => {
    const w = useProjetWizard()
    w.data.step1.nom = "Test"
    w.data.step1.description = "desc"
    w.next()
    w.data.step2.secteur = "energie"
    w.data.step2.type_impact = "mitigation_carbone"
    w.next()
    w.data.step3.localisation_pays_iso2 = "BJ"
    w.data.step3.localisation_region = "Atlantique"
    w.next()
    w.data.step4.budget = { amount: "1000000", currency: "XOF" }
    w.data.step4.horizon_mois = 24

    const store = useProjetsStore()
    const fake: ProjetRead = {
      id: "p1",
      account_id: "a",
      version: 1,
      nom: "Test",
      statut: "brouillon",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    const spy = vi.spyOn(store, "create").mockResolvedValue(fake)
    const result = await w.submit()
    expect(spy).toHaveBeenCalledWith({
      nom: "Test",
      description: "desc",
      secteur: "energie",
      type_impact: "mitigation_carbone",
      localisation_pays_iso2: "BJ",
      localisation_region: "Atlantique",
      budget: { amount: "1000000", currency: "XOF" },
      horizon_mois: 24,
    })
    expect(result).toEqual(fake)
  })

  it("reset() remet le wizard à l'état initial", () => {
    const w = useProjetWizard()
    w.data.step1.nom = "x".repeat(5)
    w.next()
    w.reset()
    expect(w.step.value).toBe(1)
    expect(w.data.step1.nom).toBe("")
  })
})
