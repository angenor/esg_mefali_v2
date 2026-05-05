// F47 T031 — Tests computeCarbonCoverage.

import { describe, expect, it } from "vitest"
import { computeCarbonCoverage } from "~/lib/computeCarbonCoverage"
import { groupCarbonByScope } from "~/lib/groupCarbonByScope"
import type { CarbonBreakdownLine } from "~/types/carbon"

function line(scope: "1" | "2" | "3", categorie: string): CarbonBreakdownLine {
  return {
    code: `${categorie}-1`,
    quantity: "1",
    unit: "kWh",
    factor_id: "f1",
    factor_value: "0.5",
    factor_source_id: "src",
    factor_version: 1,
    scope,
    categorie,
    kgco2e: "100",
  }
}

describe("computeCarbonCoverage", () => {
  it("aucune ligne → globalPct=0, isLow=true", () => {
    const cov = computeCarbonCoverage(groupCarbonByScope([]))
    expect(cov.globalPct).toBe(0)
    expect(cov.isLow).toBe(true)
  })

  it("tous postes remplis → globalPct=100, isLow=false", () => {
    const lines = [
      line("1", "combustion_fixe"),
      line("1", "combustion_mobile"),
      line("1", "fugitives"),
      line("2", "electricite"),
      line("2", "vapeur"),
      line("2", "chaleur"),
      line("2", "froid"),
      line("3", "achats"),
      line("3", "transport_amont"),
      line("3", "dechets"),
      line("3", "deplacements"),
      line("3", "transport_aval"),
    ]
    const cov = computeCarbonCoverage(groupCarbonByScope(lines))
    expect(cov.globalPct).toBe(100)
    expect(cov.scope1Pct).toBe(100)
    expect(cov.scope2Pct).toBe(100)
    expect(cov.scope3Pct).toBe(100)
    expect(cov.isLow).toBe(false)
  })

  it("Scope 2 complet seul → scope2Pct=100, globalPct=33.3", () => {
    const lines = [
      line("2", "electricite"),
      line("2", "vapeur"),
      line("2", "chaleur"),
      line("2", "froid"),
    ]
    const cov = computeCarbonCoverage(groupCarbonByScope(lines))
    expect(cov.scope2Pct).toBe(100)
    expect(cov.globalPct).toBeCloseTo(33.3, 1)
    expect(cov.isLow).toBe(true)
  })

  it("seuil strict < 60 : 60% n'est PAS low", () => {
    // 7 postes sur 12 = 58.3%
    const lines = [
      line("1", "combustion_fixe"),
      line("1", "combustion_mobile"),
      line("2", "electricite"),
      line("2", "vapeur"),
      line("2", "chaleur"),
      line("3", "achats"),
      line("3", "deplacements"),
    ]
    const cov = computeCarbonCoverage(groupCarbonByScope(lines))
    expect(cov.globalPct).toBeCloseTo(58.3, 1)
    expect(cov.isLow).toBe(true)
  })
})
