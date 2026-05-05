// F51 T020 — useComparateur : ajout/retrait/cap 3, persistance localStorage.

import { afterEach, beforeEach, describe, expect, it } from "vitest"
import { withSetup } from "../../helpers/withSetup"
import { COMPARATOR_MAX, useComparateur } from "~/composables/useComparateur"
import type { OffreMatchItem } from "~/types/matching"

function fakeOffre(id: string, label = "Offre " + id): OffreMatchItem {
  return {
    offre_id: id,
    nom: label,
    intermediaire: { id: "i" + id, nom: "Inter " + id, geolocation: null },
    type: "credit",
    montant_min: { amount: "10000", currency: "EUR" },
    montant_max: { amount: "100000", currency: "EUR" },
    duree_min_mois: 12,
    duree_max_mois: 60,
    secteurs: ["renouvelable"],
  }
}

describe("useComparateur", () => {
  beforeEach(() => {
    window.localStorage.clear()
  })
  afterEach(() => {
    window.localStorage.clear()
  })

  it("starts empty", () => {
    const [api] = withSetup(() => useComparateur())
    expect(api.count.value).toBe(0)
  })

  it("adds offres up to cap (3)", () => {
    const [api] = withSetup(() => useComparateur())
    expect(api.add(fakeOffre("a"), null)).toBe(true)
    expect(api.add(fakeOffre("b"), null)).toBe(true)
    expect(api.add(fakeOffre("c"), null)).toBe(true)
    expect(api.count.value).toBe(COMPARATOR_MAX)
    // 4th add returns false.
    expect(api.add(fakeOffre("d"), null)).toBe(false)
    expect(api.count.value).toBe(COMPARATOR_MAX)
  })

  it("is idempotent on adding the same offre twice", () => {
    const [api] = withSetup(() => useComparateur())
    api.add(fakeOffre("a"), null)
    api.add(fakeOffre("a"), null)
    expect(api.count.value).toBe(1)
  })

  it("removes an entry", () => {
    const [api] = withSetup(() => useComparateur())
    api.add(fakeOffre("a"), null)
    api.add(fakeOffre("b"), null)
    api.remove("a")
    expect(api.count.value).toBe(1)
    expect(api.has("a")).toBe(false)
    expect(api.has("b")).toBe(true)
  })

  it("persists to localStorage", () => {
    const [api] = withSetup(() => useComparateur())
    api.add(fakeOffre("a"), "p-1")
    const raw = window.localStorage.getItem("mefali:matching:comparator:v1")
    expect(raw).toBeTruthy()
    const parsed = JSON.parse(raw!)
    expect(parsed[0].offre_id).toBe("a")
    expect(parsed[0].projet_id).toBe("p-1")
  })

  it("rehydrates on a fresh instance from localStorage", () => {
    const [api1] = withSetup(() => useComparateur())
    api1.add(fakeOffre("z"), null)
    const [api2] = withSetup(() => useComparateur())
    expect(api2.has("z")).toBe(true)
  })

  it("clear() empties storage", () => {
    const [api] = withSetup(() => useComparateur())
    api.add(fakeOffre("a"), null)
    api.clear()
    expect(api.count.value).toBe(0)
    expect(window.localStorage.getItem("mefali:matching:comparator:v1")).toBe("[]")
  })
})
