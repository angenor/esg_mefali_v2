// F47 T004 — Helper pur : calcule la couverture (% postes renseignés / attendus).
//
// Cf. specs/047-empreinte-carbone-ui/data-model.md §3.3.

import type { GroupedBreakdown, ScopeBreakdown } from "~/lib/groupCarbonByScope"

export interface CoverageSnapshot {
  scope1Pct: number
  scope2Pct: number
  scope3Pct: number
  globalPct: number
  isLow: boolean
}

const LOW_THRESHOLD = 60 // strict <

function pct(filled: number, expected: number): number {
  if (expected === 0) return 0
  return Math.round((filled / expected) * 1000) / 10
}

function safeScope(grouped: GroupedBreakdown, k: "1" | "2" | "3"): ScopeBreakdown | undefined {
  return grouped[k]
}

export function computeCarbonCoverage(
  grouped: GroupedBreakdown,
): CoverageSnapshot {
  const s1 = safeScope(grouped, "1")
  const s2 = safeScope(grouped, "2")
  const s3 = safeScope(grouped, "3")

  const scope1Pct = s1 ? pct(s1.filledPostesCount, s1.expectedPostesCount) : 0
  const scope2Pct = s2 ? pct(s2.filledPostesCount, s2.expectedPostesCount) : 0
  const scope3Pct = s3 ? pct(s3.filledPostesCount, s3.expectedPostesCount) : 0

  const totalFilled =
    (s1?.filledPostesCount ?? 0) +
    (s2?.filledPostesCount ?? 0) +
    (s3?.filledPostesCount ?? 0)
  const totalExpected =
    (s1?.expectedPostesCount ?? 0) +
    (s2?.expectedPostesCount ?? 0) +
    (s3?.expectedPostesCount ?? 0)
  const globalPct = pct(totalFilled, totalExpected)

  return {
    scope1Pct,
    scope2Pct,
    scope3Pct,
    globalPct,
    isLow: globalPct < LOW_THRESHOLD,
  }
}
