// F47 T003 — Helper pur : groupe les lignes breakdown par (scope, categorie/poste).
//
// Cf. specs/047-empreinte-carbone-ui/data-model.md §3.2 + §6.

import Decimal from "decimal.js"
import type {
  CarbonBreakdownLine,
  CarbonPosteCode,
  Scope,
} from "~/types/carbon"

export const CARBON_EXPECTED_POSTS_BY_SCOPE: Record<
  Scope,
  ReadonlyArray<CarbonPosteCode>
> = {
  "1": ["combustion_fixe", "combustion_mobile", "fugitives"],
  "2": ["electricite", "vapeur", "chaleur", "froid"],
  "3": [
    "achats",
    "transport_amont",
    "dechets",
    "deplacements",
    "transport_aval",
  ],
}

export interface ScopePosteGroup {
  scope: Scope
  posteCode: CarbonPosteCode
  lines: CarbonBreakdownLine[]
  subtotalKgCo2e: string // Decimal
}

export interface ScopeBreakdown {
  scope: Scope
  totalKgCo2e: string // Decimal
  groups: ScopePosteGroup[]
  expectedPostesCount: number
  filledPostesCount: number
}

export type GroupedBreakdown = Record<Scope, ScopeBreakdown>

const SCOPES: ReadonlyArray<Scope> = ["1", "2", "3"]

function sumDecimals(values: ReadonlyArray<string>): string {
  return values
    .reduce((acc, v) => acc.plus(new Decimal(v || "0")), new Decimal(0))
    .toString()
}

export function groupCarbonByScope(
  breakdown: ReadonlyArray<CarbonBreakdownLine>,
): GroupedBreakdown {
  const result = {} as GroupedBreakdown
  for (const scope of SCOPES) {
    const expected = CARBON_EXPECTED_POSTS_BY_SCOPE[scope]
    const linesForScope = breakdown.filter((l) => l.scope === scope)
    const groups: ScopePosteGroup[] = expected.map((posteCode) => {
      const lines = linesForScope.filter((l) => l.categorie === posteCode)
      return {
        scope,
        posteCode,
        lines,
        subtotalKgCo2e: sumDecimals(lines.map((l) => l.kgco2e)),
      }
    })
    const filledPostesCount = groups.filter((g) => g.lines.length > 0).length
    result[scope] = {
      scope,
      totalKgCo2e: sumDecimals(linesForScope.map((l) => l.kgco2e)),
      groups,
      expectedPostesCount: expected.length,
      filledPostesCount,
    }
  }
  return result
}
