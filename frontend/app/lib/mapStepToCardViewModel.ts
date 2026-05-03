// F45 T012 — Helper pur projetant un ActionStep en StepCardViewModel.
import { bucketOf } from "~/lib/mapPlanToTimelineBuckets"
import type {
  ActionStep,
  Priority,
  StepCardViewModel,
  StepStatus,
} from "~/types/actionPlan"

type TFn = (key: string, params?: Record<string, string | number>) => string

const PRIORITY_TONE: Record<Priority, "danger" | "warning" | "info"> = {
  haute: "danger",
  moyenne: "warning",
  basse: "info",
}

const STATUS_TONE: Record<StepStatus, "neutral" | "progress" | "success" | "muted"> = {
  todo: "neutral",
  doing: "progress",
  done: "success",
  postponed: "muted",
}

function relativeHorizon(generatedAt: string, horizonAt: string | null, t: TFn): string {
  if (!horizonAt) return t("planAction.card.unscheduled")
  const f = new Date(generatedAt)
  const h = new Date(horizonAt)
  if (Number.isNaN(f.getTime()) || Number.isNaN(h.getTime())) {
    return t("planAction.card.unscheduled")
  }
  const months = Math.max(0, Math.round((h.getTime() - f.getTime()) / (30 * 24 * 60 * 60 * 1000)))
  if (months === 0) return t("planAction.card.horizonRelative.zero")
  if (months === 1) return t("planAction.card.horizonRelative.one")
  return t("planAction.card.horizonRelative", { n: months })
}

export interface MapStepCtx {
  generatedAt: string
  reducedMotion?: boolean
  t: TFn
  responsibleLabels?: Record<string, string>
  uiState?: { loading?: boolean; error?: string | null; overlay?: Partial<ActionStep> | null }
}

export function mapStepToCardViewModel(step: ActionStep, ctx: MapStepCtx): StepCardViewModel {
  const overlay = ctx.uiState?.overlay ?? null
  const merged: ActionStep = overlay ? { ...step, ...overlay } : step
  const responsibleLabel =
    merged.responsible_user_id && ctx.responsibleLabels?.[merged.responsible_user_id]
      ? ctx.responsibleLabels[merged.responsible_user_id]
      : merged.responsible_user_id
        ? merged.responsible_user_id.slice(0, 8)
        : ctx.t("planAction.card.notAssigned")
  const sourceLink = merged.indicateur_id
    ? {
        href: `/scoring/indicateurs/${merged.indicateur_id}`,
        label: ctx.t("planAction.card.sourceLink"),
      }
    : null
  return {
    id: merged.id,
    title: merged.title,
    description: merged.description,
    priorityLabel: ctx.t(`planAction.filters.priority.${merged.priority}`),
    priorityTone: PRIORITY_TONE[merged.priority],
    horizonAt: merged.horizon_at || null,
    horizonRelative: relativeHorizon(ctx.generatedAt, merged.horizon_at, ctx.t),
    bucket: bucketOf(merged, ctx.generatedAt),
    status: merged.status,
    statusLabel: ctx.t(`planAction.filters.status.${merged.status}`),
    statusTone: STATUS_TONE[merged.status],
    responsibleUserId: merged.responsible_user_id,
    responsibleAvatarUrl: null,
    responsibleLabel,
    indicateurId: merged.indicateur_id,
    sourceLink,
    isLoading: ctx.uiState?.loading ?? false,
    error: ctx.uiState?.error ?? null,
  }
}
