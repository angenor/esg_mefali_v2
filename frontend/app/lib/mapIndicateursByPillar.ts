// F46 T014 — Helper pur : groupe les indicateurs par pilier.
//
// Cf. specs/046-scoring-esg-ui/data-model.md §5.1.

import type {
  PillarBucketVM,
  PillarCode,
  PillarRowVM,
  ScoreDetailVM,
} from "~/types/scoring"

export const PILLAR_LABELS_FR: Record<string, string> = {
  E: "Environnement",
  S: "Social",
  G: "Gouvernance",
}

export interface SourceStatusEntry {
  status: "verified" | "revoked" | string
}

export type SourceMap = Map<string, SourceStatusEntry>

const PILLAR_ORDER: readonly PillarCode[] = ["E", "S", "G"]

function labelFor(pillar: string): string {
  return PILLAR_LABELS_FR[pillar] ?? pillar.toUpperCase()
}

function isRevoked(map: SourceMap, sourceId: string | null): boolean {
  if (!sourceId) return false
  const entry = map.get(sourceId)
  return entry?.status === "revoked"
}

export function mapIndicateursByPillar(
  detail: ScoreDetailVM | null | undefined,
  sources: SourceMap,
  editable: ReadonlySet<string>,
  scoresByPillar?: Record<PillarCode, number | null>,
): PillarBucketVM[] {
  if (!detail) return []
  const covered = detail.indicateursCouverts ?? []
  const missing = detail.indicateursManquants ?? []
  if (covered.length === 0 && missing.length === 0) return []

  const buckets = new Map<PillarCode, PillarRowVM[]>()

  for (const c of covered) {
    const row: PillarRowVM = {
      indicateurId: c.indicateurId,
      indicateurCode: c.indicateurCode,
      pillar: c.pillar,
      status: "covered",
      scoreContribution: c.contribution,
      weight: c.weight,
      normalizedValue: c.normalizedValue,
      rawValue: c.value,
      sourceId: c.sourceId,
      isSourceRevoked: isRevoked(sources, c.sourceId),
      isEditable: editable.has(c.indicateurCode),
      reason: null,
    }
    const list = buckets.get(c.pillar) ?? []
    list.push(row)
    buckets.set(c.pillar, list)
  }

  for (const m of missing) {
    const row: PillarRowVM = {
      indicateurId: m.indicateurId,
      indicateurCode: m.indicateurCode,
      pillar: m.pillar,
      status: "missing",
      scoreContribution: null,
      weight: null,
      normalizedValue: null,
      rawValue: null,
      sourceId: null,
      isSourceRevoked: false,
      isEditable: editable.has(m.indicateurCode),
      reason: m.reason,
    }
    const list = buckets.get(m.pillar) ?? []
    list.push(row)
    buckets.set(m.pillar, list)
  }

  // Tri : couverts par contribution desc puis missing en queue.
  for (const [pillar, rows] of buckets.entries()) {
    rows.sort((a, b) => {
      if (a.status === "covered" && b.status === "missing") return -1
      if (a.status === "missing" && b.status === "covered") return 1
      const ac = a.scoreContribution ?? -Infinity
      const bc = b.scoreContribution ?? -Infinity
      return bc - ac
    })
    buckets.set(pillar, rows)
  }

  // Ordre des piliers : E, S, G en premier puis le reste alphabétique.
  const orderedPillars: PillarCode[] = []
  for (const p of PILLAR_ORDER) if (buckets.has(p)) orderedPillars.push(p)
  for (const p of Array.from(buckets.keys()).sort()) {
    if (!orderedPillars.includes(p)) orderedPillars.push(p)
  }

  const scoreMap = scoresByPillar ?? detail.scoresByPillar ?? {}

  return orderedPillars.map((pillar) => ({
    pillar,
    pillarLabel: labelFor(pillar),
    scoreByPillar: scoreMap[pillar] ?? null,
    rows: buckets.get(pillar) ?? [],
  }))
}
