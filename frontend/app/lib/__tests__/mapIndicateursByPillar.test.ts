// F46 T013 — Tests pour mapIndicateursByPillar (helper pur).
//
// Cf. specs/046-scoring-esg-ui/data-model.md §5.1.

import { describe, it, expect } from "vitest"
import { mapIndicateursByPillar } from "../mapIndicateursByPillar"
import type {
  CoveredIndicatorVM,
  MissingIndicatorVM,
  ScoreDetailVM,
} from "~/types/scoring"

function covered(
  partial: Partial<CoveredIndicatorVM> & { indicateurCode: string; pillar: string },
): CoveredIndicatorVM {
  return {
    indicateurId: partial.indicateurId ?? `id-${partial.indicateurCode}`,
    indicateurCode: partial.indicateurCode,
    pillar: partial.pillar,
    value: partial.value ?? 100,
    normalizedValue: partial.normalizedValue ?? 80,
    weight: partial.weight ?? 1,
    contribution: partial.contribution ?? 50,
    sourceId: partial.sourceId ?? `src-${partial.indicateurCode}`,
  }
}

function missing(
  partial: Partial<MissingIndicatorVM> & { indicateurCode: string; pillar: string },
): MissingIndicatorVM {
  return {
    indicateurId: partial.indicateurId ?? `id-${partial.indicateurCode}`,
    indicateurCode: partial.indicateurCode,
    pillar: partial.pillar,
    reason: partial.reason ?? "value_absent",
  }
}

function makeDetail(
  c: CoveredIndicatorVM[],
  m: MissingIndicatorVM[],
): ScoreDetailVM {
  return {
    referentielCode: "BOAD",
    referentielId: "ref-1",
    referentielVersion: 1,
    scoreGlobal: 60,
    scoresByPillar: { E: 60, S: 70, G: 50 },
    coverageRatio: 0.5,
    computedAt: "2026-05-04T12:00:00Z",
    indicateursCouverts: c,
    indicateursManquants: m,
    sourcesUsed: [],
  }
}

describe("mapIndicateursByPillar", () => {
  it("(a) groupe E/S/G + couverts triés par contribution desc, missing en queue", () => {
    const c = [
      covered({ indicateurCode: "E1", pillar: "E", contribution: 30 }),
      covered({ indicateurCode: "E2", pillar: "E", contribution: 60 }),
      covered({ indicateurCode: "S1", pillar: "S", contribution: 40 }),
    ]
    const m = [
      missing({ indicateurCode: "G_MISS", pillar: "G" }),
      missing({ indicateurCode: "E_MISS", pillar: "E" }),
    ]
    const detail = makeDetail(c, m)
    const buckets = mapIndicateursByPillar(detail, new Map(), new Set())

    expect(buckets.map((b) => b.pillar)).toEqual(["E", "S", "G"])
    const ePillar = buckets[0]!
    expect(ePillar.rows.map((r) => r.indicateurCode)).toEqual([
      "E2",
      "E1",
      "E_MISS",
    ])
    expect(ePillar.rows[2]!.status).toBe("missing")
  })

  it("(b) source révoquée → isSourceRevoked=true", () => {
    const detail = makeDetail(
      [covered({ indicateurCode: "E1", pillar: "E", sourceId: "src-A" })],
      [],
    )
    const sources = new Map<string, { status: "verified" | "revoked" }>([
      ["src-A", { status: "revoked" }],
    ])
    const buckets = mapIndicateursByPillar(detail, sources, new Set())
    expect(buckets[0]!.rows[0]!.isSourceRevoked).toBe(true)
  })

  it("(c) indicateur dans editable → isEditable=true", () => {
    const detail = makeDetail(
      [covered({ indicateurCode: "EFFECTIFS_TOTAL", pillar: "S" })],
      [],
    )
    const editable = new Set(["EFFECTIFS_TOTAL"])
    const buckets = mapIndicateursByPillar(detail, new Map(), editable)
    expect(buckets[0]!.rows[0]!.isEditable).toBe(true)
  })

  it("(d) pilier custom → label = code en majuscules", () => {
    const detail = makeDetail(
      [covered({ indicateurCode: "X1", pillar: "custom" })],
      [],
    )
    const buckets = mapIndicateursByPillar(detail, new Map(), new Set())
    expect(buckets[0]!.pillarLabel).toBe("CUSTOM")
  })

  it("(e) détail vide → tableau vide", () => {
    const detail = makeDetail([], [])
    expect(mapIndicateursByPillar(detail, new Map(), new Set())).toEqual([])
  })
})
