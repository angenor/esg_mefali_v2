// F45 T011 — Helper pur regroupant les étapes d'un ActionPlan en buckets
// d'horizon temporel. Cf. data-model.md § 2.3.
import type {
  ActionPlan,
  ActionStep,
  TimelineBucket,
  TimelineBucketViewModel,
  TimelineViewModel,
} from "~/types/actionPlan"

const BUCKET_ORDER: TimelineBucket[] = ["lt3m", "3to6m", "6to12m", "12to24m", "unscheduled"]

const BUCKET_LABELS: Record<TimelineBucket, string> = {
  lt3m: "Moins de 3 mois",
  "3to6m": "3 à 6 mois",
  "6to12m": "6 à 12 mois",
  "12to24m": "12 à 24 mois",
  unscheduled: "Sans échéance",
}

const MS_PER_DAY = 24 * 60 * 60 * 1000

function deltaMonths(from: string, to: string | null | undefined): number | null {
  if (!to) return null
  const f = new Date(from)
  const t = new Date(to)
  if (Number.isNaN(f.getTime()) || Number.isNaN(t.getTime())) return null
  const days = (t.getTime() - f.getTime()) / MS_PER_DAY
  return Math.round(days / 30)
}

export function bucketOf(step: ActionStep, generatedAt: string): TimelineBucket {
  const months = deltaMonths(generatedAt, step.horizon_at)
  if (months === null) return "unscheduled"
  if (months <= 3) return "lt3m"
  if (months <= 6) return "3to6m"
  if (months <= 12) return "6to12m"
  return "12to24m"
}

function rangeFor(bucket: TimelineBucket, generatedAt: string): {
  rangeStart: string | null
  rangeEnd: string | null
} {
  if (bucket === "unscheduled") return { rangeStart: null, rangeEnd: null }
  const base = new Date(generatedAt)
  const months: Record<Exclude<TimelineBucket, "unscheduled">, [number, number]> = {
    lt3m: [0, 3],
    "3to6m": [3, 6],
    "6to12m": [6, 12],
    "12to24m": [12, 24],
  }
  const [a, b] = months[bucket as Exclude<TimelineBucket, "unscheduled">]
  const start = new Date(base)
  start.setMonth(start.getMonth() + a)
  const end = new Date(base)
  end.setMonth(end.getMonth() + b)
  return {
    rangeStart: start.toISOString().slice(0, 10),
    rangeEnd: end.toISOString().slice(0, 10),
  }
}

/**
 * Squelette TimelineViewModel sans les `steps` projetés en
 * StepCardViewModel (la projection se fait dans la page avec le contexte i18n).
 */
export function mapPlanToTimelineBuckets(plan: ActionPlan): TimelineViewModel {
  const buckets: TimelineBucketViewModel[] = BUCKET_ORDER.map((b) => ({
    bucket: b,
    label: BUCKET_LABELS[b],
    ...rangeFor(b, plan.generated_at),
    steps: [],
  }))
  // Index les steps bruts par bucket pour exposer une vue ordonnée. La page
  // remplacera `steps` par les ViewModels projetés.
  const bucketIndex: Record<TimelineBucket, ActionStep[]> = {
    lt3m: [],
    "3to6m": [],
    "6to12m": [],
    "12to24m": [],
    unscheduled: [],
  }
  for (const step of plan.steps) {
    bucketIndex[bucketOf(step, plan.generated_at)].push(step)
  }
  // On ne projette pas vers StepCardViewModel ici (helper pur, sans i18n).
  // La page injectera mapStepToCardViewModel sur ces tableaux après.
  return {
    generatedAt: plan.generated_at,
    horizonMonths: plan.horizon_months,
    buckets,
  }
}

export function groupStepsByBucket(plan: ActionPlan): Record<TimelineBucket, ActionStep[]> {
  const out: Record<TimelineBucket, ActionStep[]> = {
    lt3m: [],
    "3to6m": [],
    "6to12m": [],
    "12to24m": [],
    unscheduled: [],
  }
  for (const step of plan.steps) {
    out[bucketOf(step, plan.generated_at)].push(step)
  }
  return out
}

export const TIMELINE_BUCKET_ORDER = BUCKET_ORDER
export const TIMELINE_BUCKET_LABELS = BUCKET_LABELS
