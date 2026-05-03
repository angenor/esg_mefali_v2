// F45 T015 — Parse / serialize URL query string pour les filtres du plan d'action.
//
// Validation silencieuse (FR-007) : valeur invalide → ignorée, pas d'erreur.
import { computed, type ComputedRef } from "vue"
import { useActionPlanStore } from "~/stores/actionPlan"
import type { Horizon, PlanFilters, Priority, StepStatus } from "~/types/actionPlan"

const PRIORITY_VALUES: Priority[] = ["haute", "moyenne", "basse"]
const STATUS_VALUES: StepStatus[] = ["todo", "doing", "done", "postponed"]
const HORIZON_VALUES: Horizon[] = [6, 12, 24]
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function parseList<T extends string>(raw: string | undefined, allowed: readonly T[]): T[] {
  if (!raw) return []
  return raw
    .split(",")
    .map((v) => v.trim())
    .filter((v): v is T => (allowed as readonly string[]).includes(v))
}

export function parseFiltersFromQuery(query: Record<string, unknown>): PlanFilters {
  const get = (key: string): string | undefined => {
    const v = query[key]
    if (Array.isArray(v)) return v[0] as string | undefined
    return typeof v === "string" ? v : undefined
  }
  const horizonRaw = get("horizon")
  const horizon = horizonRaw && /^\d+$/.test(horizonRaw)
    ? (HORIZON_VALUES.find((h) => h === Number(horizonRaw)) ?? null)
    : null
  const responsibleRaw = get("responsible")
  const responsible = responsibleRaw && UUID_RE.test(responsibleRaw) ? responsibleRaw : null
  return {
    priority: parseList(get("priority"), PRIORITY_VALUES),
    status: parseList(get("status"), STATUS_VALUES),
    horizon,
    responsibleUserId: responsible,
  }
}

export function serializeFiltersToQuery(filters: PlanFilters): Record<string, string> {
  const q: Record<string, string> = {}
  if (filters.priority.length) q.priority = filters.priority.join(",")
  if (filters.status.length) q.status = filters.status.join(",")
  if (filters.horizon !== null) q.horizon = String(filters.horizon)
  if (filters.responsibleUserId) q.responsible = filters.responsibleUserId
  return q
}

export interface UseActionPlanFilters {
  filters: ComputedRef<PlanFilters>
  setFilters(next: Partial<PlanFilters>): void
  resetFilters(): void
  hasActive: ComputedRef<boolean>
}

interface RouterLike {
  replace(loc: { query: Record<string, string> }): unknown
}

interface RouteLike {
  query: Record<string, unknown>
}

function safeUseRoute(): RouteLike {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fn = (globalThis as any).useRoute as (() => RouteLike) | undefined
  if (fn) return fn()
  return { query: {} }
}

function safeUseRouter(): RouterLike {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fn = (globalThis as any).useRouter as (() => RouterLike) | undefined
  if (fn) return fn()
  return { replace: () => undefined }
}

export function useActionPlanFilters(): UseActionPlanFilters {
  const store = useActionPlanStore()
  const route = safeUseRoute()
  const router = safeUseRouter()

  // Hydratation initiale depuis l'URL.
  const fromQuery = parseFiltersFromQuery(route.query)
  store.setFilters(fromQuery)

  const filters = computed<PlanFilters>(() => store.filters)

  const hasActive = computed(
    () =>
      filters.value.priority.length > 0 ||
      filters.value.status.length > 0 ||
      filters.value.horizon !== null ||
      filters.value.responsibleUserId !== null,
  )

  function setFilters(next: Partial<PlanFilters>): void {
    store.setFilters(next)
    router.replace({ query: serializeFiltersToQuery(store.filters) })
  }

  function resetFilters(): void {
    store.resetFilters()
    router.replace({ query: {} })
  }

  return { filters, setFilters, resetFilters, hasActive }
}
