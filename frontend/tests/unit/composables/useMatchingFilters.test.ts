// F51 T019 — useMatchingFilters : parseQuery / toQuery.

import { describe, expect, it } from "vitest"
import {
  parseQuery,
  shallowEqual,
  toQuery,
} from "~/composables/useMatchingFilters"

describe("parseQuery", () => {
  it("extracts known filters and ignores unknown values", () => {
    const f = parseQuery({
      type: "subvention",
      montant_max_eur: "100000",
      duree_min_mois: "12",
      secteur: "Renouvelable",
      foo: "bar",
    })
    expect(f.type).toBe("subvention")
    expect(f.montant_max_eur).toBe(100000)
    expect(f.duree_min_mois).toBe(12)
    expect(f.secteur).toBe("renouvelable") // lowercased
    expect("foo" in f).toBe(false)
  })

  it("rejects an invalid type", () => {
    const f = parseQuery({ type: "exotic" })
    expect(f.type).toBeUndefined()
  })

  it("rejects negative or non-numeric montant", () => {
    expect(parseQuery({ montant_min_eur: "not-a-number" }).montant_min_eur).toBeUndefined()
    expect(parseQuery({ montant_min_eur: "-100" }).montant_min_eur).toBeUndefined()
  })

  it("accepts simulateur CTA shorthand (montant_max, duree_max)", () => {
    const f = parseQuery({ montant_max: "150000", duree_max: "84" })
    expect(f.montant_max_eur).toBe(150000)
    expect(f.duree_max_mois).toBe(84)
  })

  it("prefers the suffixed canonical when both are provided", () => {
    const f = parseQuery({
      montant_max_eur: "200000",
      montant_max: "150000",
      duree_max_mois: "120",
      duree_max: "84",
    })
    expect(f.montant_max_eur).toBe(200000)
    expect(f.duree_max_mois).toBe(120)
  })
})

describe("toQuery", () => {
  it("serializes only defined values", () => {
    const out = toQuery({ type: "credit", montant_max_eur: 50000 })
    expect(out).toEqual({ type: "credit", montant_max_eur: "50000" })
  })

  it("drops empty strings", () => {
    const out = toQuery({ q: "" })
    expect(out).toEqual({})
  })
})

describe("shallowEqual", () => {
  it("returns true on identical objects", () => {
    expect(shallowEqual({ a: "1" }, { a: "1" })).toBe(true)
  })
  it("returns false on differing values", () => {
    expect(shallowEqual({ a: "1" }, { a: "2" })).toBe(false)
  })
  it("returns false on differing keys", () => {
    expect(shallowEqual({ a: "1" }, { a: "1", b: "2" })).toBe(false)
  })
})
