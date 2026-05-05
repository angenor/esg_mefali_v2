// F45 T002 — Types miroir des schemas backend F31 (ActionPlan, ActionStep) +
// ViewModels UI dérivés. Cf. specs/045-plan-action-ui/data-model.md § 1-2.

export type Priority = "haute" | "moyenne" | "basse"
export type StepStatus = "todo" | "doing" | "done" | "postponed"
export type Category = "esg" | "carbone" | "credit" | "candidature"
export type Horizon = 6 | 12 | 24

export interface ActionStep {
  id: string
  plan_id: string
  title: string
  description: string | null
  category: Category
  priority: Priority
  horizon_at: string
  status: StepStatus
  responsible_user_id: string | null
  indicateur_id: string | null
  source_id: string | null
  created_at: string
  updated_at: string
}

export interface ActionPlan {
  id: string
  account_id: string
  horizon_months: Horizon
  version: number
  score_calculation_id: string | null
  generated_at: string
  generated_by_user_id: string | null
  steps: ActionStep[]
}

export interface ActionStepPatchPayload {
  status?: StepStatus
  responsible_user_id?: string | null
}

export interface PlanFilters {
  priority: Priority[]
  status: StepStatus[]
  horizon: Horizon | null
  responsibleUserId: string | null
}

export type TimelineBucket = "lt3m" | "3to6m" | "6to12m" | "12to24m" | "unscheduled"

export interface StepCardViewModel {
  id: string
  title: string
  description: string | null
  priorityLabel: string
  priorityTone: "danger" | "warning" | "info"
  horizonAt: string | null
  horizonRelative: string
  bucket: TimelineBucket
  status: StepStatus
  statusLabel: string
  statusTone: "neutral" | "progress" | "success" | "muted"
  responsibleUserId: string | null
  responsibleAvatarUrl: string | null
  responsibleLabel: string
  indicateurId: string | null
  sourceLink: { href: string; label: string } | null
  isLoading: boolean
  error: string | null
}

export interface TimelineBucketViewModel {
  bucket: TimelineBucket
  label: string
  rangeStart: string | null
  rangeEnd: string | null
  steps: StepCardViewModel[]
}

export interface TimelineViewModel {
  generatedAt: string
  horizonMonths: Horizon
  buckets: TimelineBucketViewModel[]
}

export interface CompletionStats {
  totalVisible: number
  doneVisible: number
  percent: number
  hasData: boolean
}

export interface ResponsibleOption {
  id: string
  label: string
}
