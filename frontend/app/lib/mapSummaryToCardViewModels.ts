// F44 T009 — Adapter pur : DashboardSummaryOut → ViewModels par carte.
//
// Cf. specs/044-dashboard-pme-ui/data-model.md et contracts/frontend-components.md C-LIB-1.
import type {
  ActionStepEntry,
  AttestationRecent,
  CandidatureRecent,
  CarbonEntry,
  DashboardSummaryOut,
  RapportRecent,
  ScoreEntry,
} from "~/stores/dashboard"
import type { BlockKey } from "~/lib/dashboardEventMap"

export type CardKind<T> =
  | { kind: "loading" }
  | { kind: "empty"; cta: { label: string; href: string }; message: string }
  | { kind: "filled"; data: T }
  | { kind: "error"; message: string; retry: () => void }

export interface ScoringCardData {
  scoreGlobal: number
  byAxis: { e: number; s: number; g: number }
  referentielCode: string
  referentielVersion: number
  computedAt: Date
  sourceCount: number
  href: string
}

export interface CarbonCardData {
  totalAnnualTco2e: string
  year: number
  trend: { quarter: string; tco2e: string }[]
  computedAt: Date
  href: string
  /** Nb sources documentaires utilisées pour le calcul (TODO post-MVP F32). */
  sourceCount?: number
}

export interface CreditCardData {
  combineScore: number
  solvabilite: number
  impactVert: number
  eligibilityBadges: string[]
  coherenceWarning: boolean
  computedAt: Date
  href: string
}

export interface CandidatureRecentVM {
  id: string
  projetLabel: string
  offreLabel: string
  statut: string
  statutLabel: string
  soumissionAt: Date | null
}

export interface CandidaturesCardData {
  countersByStatut: Record<string, number>
  total: number
  recent: CandidatureRecentVM[]
  href: string
}

export interface RapportsCardData {
  recentRapports: {
    id: string
    title: string
    referentielsLabel: string
    generatedAt: Date
    downloadHref: string
  }[]
  activeAttestations: {
    id: string
    publicId: string
    generatedAt: Date
    validUntil: Date
    verifyHref: string
  }[]
  href: string
}

export interface ActionPlanCardData {
  steps: {
    id: string
    title: string
    category: string
    priority: "haute" | "moyenne" | "basse"
    horizonAt: Date
  }[]
  href: string
}

export interface IntermediairesCardData {
  pins: {
    id: string
    label: string
    type: "fond" | "banque" | "autre"
    lat: number
    lng: number
  }[]
  href: string
}

export interface DashboardCardViewModels {
  scoring: CardKind<ScoringCardData>
  carbon: CardKind<CarbonCardData>
  credit: CardKind<CreditCardData>
  candidatures: CardKind<CandidaturesCardData>
  rapports: CardKind<RapportsCardData>
  actionPlan: CardKind<ActionPlanCardData>
  intermediaires: CardKind<IntermediairesCardData> | null
}

export interface MapOptions {
  t: (key: string) => string
  hasProjet: boolean
  isLoading: boolean
  blockErrors: Partial<Record<BlockKey | "*", string>>
  onRetry: (block: BlockKey) => void
  /** Optionnel : utilisé par les tests pour figer la date courante (filtre attestations). */
  now?: Date
}

const PRIORITY_ORDER: Record<"haute" | "moyenne" | "basse", number> = {
  haute: 0,
  moyenne: 1,
  basse: 2,
}

const STATUT_KEY_PREFIX = "dashboard.statut.candidature."

function loading<T>(): CardKind<T> {
  return { kind: "loading" }
}

function empty<T>(label: string, href: string, message: string): CardKind<T> {
  return { kind: "empty", cta: { label, href }, message }
}

function errorVM<T>(message: string, retry: () => void): CardKind<T> {
  return { kind: "error", message, retry }
}

function pickLatestScore(scores: ScoreEntry[]): ScoreEntry | null {
  if (scores.length === 0) return null
  return scores.reduce((acc, s) =>
    new Date(s.computed_at).getTime() > new Date(acc.computed_at).getTime() ? s : acc,
  )
}

function pickLatestCarbon(entries: CarbonEntry[]): CarbonEntry | null {
  if (entries.length === 0) return null
  return entries.reduce((acc, e) => (e.year > acc.year ? e : acc))
}

function deriveEligibilityBadges(combine: number, fromBackend?: string[] | null): string[] {
  if (fromBackend && fromBackend.length > 0) return fromBackend
  const badges: string[] = []
  if (combine >= 60) badges.push("BOAD")
  if (combine >= 75) badges.push("SUNREF")
  return badges
}

function buildScoring(
  summary: DashboardSummaryOut | null,
  opts: MapOptions,
): CardKind<ScoringCardData> {
  const errMsg = opts.blockErrors.scores ?? opts.blockErrors["*"]
  if (errMsg) return errorVM(errMsg, () => opts.onRetry("scores"))
  if (!summary && opts.isLoading) return loading()
  const scores = summary?.scores ?? []
  if (scores.length === 0) {
    return empty(
      opts.t("dashboard.cards.scoring.empty_cta"),
      "/scoring",
      opts.t("dashboard.cards.scoring.empty_message"),
    )
  }
  const latest = pickLatestScore(scores)!
  const scoreNum = Number(latest.score_global)
  return {
    kind: "filled",
    data: {
      scoreGlobal: scoreNum,
      byAxis: latest.by_axis ?? { e: scoreNum, s: scoreNum, g: scoreNum },
      referentielCode: latest.referentiel_code,
      referentielVersion: latest.referentiel_version,
      computedAt: new Date(latest.computed_at),
      sourceCount: latest.source_count ?? 0,
      href: "/scoring",
    },
  }
}

function buildCarbon(
  summary: DashboardSummaryOut | null,
  opts: MapOptions,
): CardKind<CarbonCardData> {
  const errMsg = opts.blockErrors.carbon ?? opts.blockErrors["*"]
  if (errMsg) return errorVM(errMsg, () => opts.onRetry("carbon"))
  if (!summary && opts.isLoading) return loading()
  const carbon = summary?.carbon ?? []
  if (carbon.length === 0) {
    return empty(
      opts.t("dashboard.cards.carbon.empty_cta"),
      "/carbone",
      opts.t("dashboard.cards.carbon.empty_message"),
    )
  }
  const latest = pickLatestCarbon(carbon)!
  return {
    kind: "filled",
    data: {
      totalAnnualTco2e: latest.total_tco2e,
      year: latest.year,
      trend: latest.trend ?? [],
      computedAt: new Date(latest.computed_at),
      href: "/carbone",
    },
  }
}

function buildCredit(
  summary: DashboardSummaryOut | null,
  opts: MapOptions,
): CardKind<CreditCardData> {
  const errMsg = opts.blockErrors.credit_score ?? opts.blockErrors["*"]
  if (errMsg) return errorVM(errMsg, () => opts.onRetry("credit_score"))
  if (!summary && opts.isLoading) return loading()
  const credit = summary?.credit_score ?? null
  if (!credit) {
    return empty(
      opts.t("dashboard.cards.credit.empty_cta"),
      "/credit-score",
      opts.t("dashboard.cards.credit.empty_message"),
    )
  }
  return {
    kind: "filled",
    data: {
      combineScore: credit.combine,
      solvabilite: credit.solvabilite,
      impactVert: credit.impact_vert,
      eligibilityBadges: deriveEligibilityBadges(credit.combine, credit.eligibility_badges),
      coherenceWarning: credit.coherence_warning,
      computedAt: new Date(credit.computed_at),
      href: "/credit-score",
    },
  }
}

function buildCandidatures(
  summary: DashboardSummaryOut | null,
  opts: MapOptions,
): CardKind<CandidaturesCardData> {
  const errMsg = opts.blockErrors.candidatures ?? opts.blockErrors["*"]
  if (errMsg) return errorVM(errMsg, () => opts.onRetry("candidatures"))
  if (!summary && opts.isLoading) return loading()
  const block = summary?.candidatures
  if (!block || block.total === 0) {
    return empty(
      opts.t("dashboard.cards.candidatures.empty_cta"),
      "/candidatures",
      opts.t("dashboard.cards.candidatures.empty_message"),
    )
  }
  const recent: CandidatureRecentVM[] = block.recent.slice(0, 3).map((c: CandidatureRecent) => ({
    id: c.id,
    projetLabel: c.projet_label ?? c.projet_id.slice(0, 8),
    offreLabel: c.offre_label ?? c.offre_id.slice(0, 8),
    statut: c.statut,
    statutLabel: opts.t(`${STATUT_KEY_PREFIX}${c.statut}`),
    soumissionAt: c.soumission_at ? new Date(c.soumission_at) : null,
  }))
  return {
    kind: "filled",
    data: {
      countersByStatut: block.counters_by_statut,
      total: block.total,
      recent,
      href: "/candidatures",
    },
  }
}

function buildRapports(
  summary: DashboardSummaryOut | null,
  opts: MapOptions,
): CardKind<RapportsCardData> {
  const errMsg = opts.blockErrors.rapports ?? opts.blockErrors.attestations ?? opts.blockErrors["*"]
  if (errMsg) return errorVM(errMsg, () => opts.onRetry("rapports"))
  if (!summary && opts.isLoading) return loading()
  const rapports = summary?.rapports?.recent ?? []
  const attestations = summary?.attestations?.recent ?? []
  const now = (opts.now ?? new Date()).getTime()
  const activeAttestations = attestations
    .filter((a: AttestationRecent) => {
      if (a.revoked_at) return false
      return new Date(a.valid_until).getTime() > now
    })
    .slice(0, 2)
    .map((a: AttestationRecent) => ({
      id: a.id,
      publicId: a.public_id,
      generatedAt: new Date(a.generated_at),
      validUntil: new Date(a.valid_until),
      verifyHref: `/verify/${a.public_id}`,
    }))
  const recentRapports = rapports.slice(0, 3).map((r: RapportRecent) => ({
    id: r.id,
    title: r.title ?? `Rapport ${r.entity_type}`,
    referentielsLabel: r.referentiels.join(" · "),
    generatedAt: new Date(r.generated_at),
    downloadHref: r.download_href ?? `/rapports/${r.id}.pdf`,
  }))
  if (recentRapports.length === 0 && activeAttestations.length === 0) {
    return empty(
      opts.t("dashboard.cards.rapports.empty_cta"),
      "/rapports",
      opts.t("dashboard.cards.rapports.empty_message"),
    )
  }
  return {
    kind: "filled",
    data: {
      recentRapports,
      activeAttestations,
      href: "/rapports",
    },
  }
}

function buildActionPlan(
  summary: DashboardSummaryOut | null,
  opts: MapOptions,
): CardKind<ActionPlanCardData> {
  const errMsg = opts.blockErrors.next_actions ?? opts.blockErrors["*"]
  if (errMsg) return errorVM(errMsg, () => opts.onRetry("next_actions"))
  if (!summary && opts.isLoading) return loading()
  const steps = (summary?.next_actions ?? []).filter((s: ActionStepEntry) => s.status === "pending")
  if (steps.length === 0) {
    return empty(
      opts.t("dashboard.cards.action_plan.empty_cta"),
      "/plan-action",
      opts.t("dashboard.cards.action_plan.empty_message"),
    )
  }
  const sorted = [...steps].sort((a, b) => {
    const pa = PRIORITY_ORDER[a.priority]
    const pb = PRIORITY_ORDER[b.priority]
    if (pa !== pb) return pa - pb
    return new Date(a.horizon_at).getTime() - new Date(b.horizon_at).getTime()
  })
  return {
    kind: "filled",
    data: {
      steps: sorted.slice(0, 3).map((s) => ({
        id: s.id,
        title: s.title,
        category: s.category,
        priority: s.priority,
        horizonAt: new Date(s.horizon_at),
      })),
      href: "/plan-action",
    },
  }
}

export function mapSummaryToCardViewModels(
  summary: DashboardSummaryOut | null,
  options: MapOptions,
): DashboardCardViewModels {
  return {
    scoring: buildScoring(summary, options),
    carbon: buildCarbon(summary, options),
    credit: buildCredit(summary, options),
    candidatures: buildCandidatures(summary, options),
    rapports: buildRapports(summary, options),
    actionPlan: buildActionPlan(summary, options),
    intermediaires: options.hasProjet
      ? // Carte chargée par lazy fetch côté composant : exposé en 'loading' par défaut.
        loading<IntermediairesCardData>()
      : null,
  }
}
