// F47 T030 — Tests groupCarbonByScope.

import { describe, expect, it } from "vitest"
import {
  CARBON_EXPECTED_POSTS_BY_SCOPE,
  groupCarbonByScope,
} from "~/lib/groupCarbonByScope"
import type { CarbonBreakdownLine } from "~/types/carbon"

function line(
  scope: "1" | "2" | "3",
  categorie: string,
  kg: string,
  code = `${categorie}-1`,
): CarbonBreakdownLine {
  return {
    code,
    quantity: "1",
    unit: "kWh",
    factor_id: "f1",
    factor_value: "0.5",
    factor_source_id: "src",
    factor_version: 1,
    scope,
    categorie,
    kgco2e: kg,
  }
}

describe("groupCarbonByScope", () => {
  it("breakdown vide → 3 scopes avec groups vides", () => {
    const grouped = groupCarbonByScope([])
    expect(Object.keys(grouped).sort()).toEqual(["1", "2", "3"])
    expect(grouped["1"].expectedPostesCount).toBe(3)
    expect(grouped["2"].expectedPostesCount).toBe(4)
    expect(grouped["3"].expectedPostesCount).toBe(5)
    expect(grouped["1"].filledPostesCount).toBe(0)
    expect(grouped["1"].groups.every((g) => g.lines.length === 0)).toBe(true)
  })

  it("ligne S2 électricité unique → filledPostesCount=1 sur Scope 2", () => {
    const grouped = groupCarbonByScope([line("2", "electricite", "5000")])
    expect(grouped["2"].filledPostesCount).toBe(1)
    expect(grouped["1"].filledPostesCount).toBe(0)
    const elecGroup = grouped["2"].groups.find(
      (g) => g.posteCode === "electricite",
    )
    expect(elecGroup?.lines).toHaveLength(1)
    expect(elecGroup?.subtotalKgCo2e).toBe("5000")
  })

  it("plusieurs lignes même poste → regroupées avec subtotal exact", () => {
    const grouped = groupCarbonByScope([
      line("2", "electricite", "5000", "elec-1"),
      line("2", "electricite", "2500", "elec-2"),
    ])
    const elecGroup = grouped["2"].groups.find(
      (g) => g.posteCode === "electricite",
    )
    expect(elecGroup?.lines).toHaveLength(2)
    expect(elecGroup?.subtotalKgCo2e).toBe("7500")
  })

  it("ordre des groupes = ordre de CARBON_EXPECTED_POSTS_BY_SCOPE", () => {
    const grouped = groupCarbonByScope([])
    expect(grouped["3"].groups.map((g) => g.posteCode)).toEqual(
      CARBON_EXPECTED_POSTS_BY_SCOPE["3"],
    )
  })

  it("totalKgCo2e du scope = somme des lignes du scope", () => {
    const grouped = groupCarbonByScope([
      line("2", "electricite", "5000"),
      line("2", "vapeur", "1000"),
    ])
    expect(grouped["2"].totalKgCo2e).toBe("6000")
  })
})
