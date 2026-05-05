// F45 T014/T054 — Fetch initial du plan d'action + abonnement EventBus chat.
//
// Cf. specs/045-plan-action-ui/contracts/chat-eventbus-sync.md.
import { computed, onBeforeUnmount, onMounted, ref, type ComputedRef, type Ref } from "vue"
import { useActionPlanStore } from "~/stores/actionPlan"
import { useChatEventBus } from "~/composables/useChatEventBus"
import type { EventBusEvent } from "~/types/chat"
import type { ActionPlan } from "~/types/actionPlan"

export type PlanEmptyKind = "ok" | "no_scoring" | "no_gaps" | "error"

interface RuntimeConfigShape {
  public?: { apiBase?: string }
}

function apiBase(): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const cfg = (globalThis as any).useRuntimeConfig?.() as RuntimeConfigShape | undefined
  return String(cfg?.public?.apiBase ?? "").replace(/\/$/, "")
}

type FetchFn = <T>(u: string, o?: Record<string, unknown>) => Promise<T>
function fetcher(): FetchFn | null {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return ((globalThis as any).$fetch as FetchFn | undefined) ?? null
}

export interface UseActionPlanApi {
  plan: ComputedRef<ActionPlan | null>
  loading: ComputedRef<boolean>
  error: ComputedRef<string | null>
  emptyKind: Ref<PlanEmptyKind>
  fetchPlan(force?: boolean): Promise<void>
  invalidateStep(stepId: string): Promise<void>
}

interface ScoringSummary {
  // shape minimal — F23 expose au moins ces champs
  has_scoring?: boolean
  has_gaps?: boolean
}

async function detectScoring(): Promise<"no_scoring" | "no_gaps" | "ok"> {
  const f = fetcher()
  if (!f) return "ok"
  try {
    const url = `${apiBase()}/me/scoring/summary`
    const data = await f<ScoringSummary>(url, { credentials: "include" })
    if (data?.has_scoring === false) return "no_scoring"
    if (data?.has_gaps === false) return "no_gaps"
    return "ok"
  } catch {
    // Si l'endpoint n'existe pas / 404 → on retombe sur "no_scoring" (le funnel
    // dirige vers /scoring), CTA fallback côté UI déjà affiché.
    return "no_scoring"
  }
}

export function useActionPlan(): UseActionPlanApi {
  const store = useActionPlanStore()
  const bus = useChatEventBus()
  const emptyKind = ref<PlanEmptyKind>("ok")

  const handler = (event: EventBusEvent): void => {
    if (event.eventType !== "entity_updated") return
    if (event.entityType === "action_step") {
      if (store.isEcho(event.entityId)) return
      void store.invalidateStep(event.entityId)
    } else if (event.entityType === "action_plan") {
      void store.fetchPlan(true).then(() => {
        emptyKind.value = "ok"
      })
    }
  }

  let unsubscribe: (() => void) | null = null

  async function load(force = false): Promise<void> {
    try {
      await store.fetchPlan(force)
      emptyKind.value = "ok"
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      // 404 → pas de plan : déterminer pourquoi (pas de scoring vs pas de gaps)
      if (/\b404\b/.test(msg) || /no_plan/.test(msg) || msg === "404") {
        emptyKind.value = await detectScoring()
      } else {
        emptyKind.value = "error"
      }
    }
  }

  onMounted(() => {
    unsubscribe = bus.on("entity_updated", handler)
    void load()
  })

  onBeforeUnmount(() => {
    unsubscribe?.()
    unsubscribe = null
  })

  // T061 — exposer le bus en mode dev/test pour les e2e Chat sync.
  if (typeof window !== "undefined") {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(window as any).__chatBus = bus
  }

  return {
    plan: computed(() => store.plan),
    loading: computed(() => store.loading),
    error: computed(() => store.error),
    emptyKind,
    fetchPlan: load,
    invalidateStep: (stepId: string) => store.invalidateStep(stepId),
  }
}
