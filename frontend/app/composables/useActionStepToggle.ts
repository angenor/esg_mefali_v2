// F44 T036 — Composable de toggle d'étape de plan d'action depuis le dashboard.
//
// Cf. specs/044-dashboard-pme-ui/tasks.md T034.
// - Appelle PATCH /me/action-plan/steps/{id} avec body { status: 'done' }.
// - Optimistic update : le composant masque/grise l'étape pendant l'appel.
// - Anti-loop : track l'id 5 s via store dashboard pour ignorer l'event remote
//   `action_step:completed` correspondant.
// - Émet `action_step:completed` sur le bus dashboard avec source: 'dashboard'.
// - Invalide + refetch le bloc `next_actions`.
import { computed, ref, type ComputedRef } from "vue"
import { useDashboardStore } from "~/stores/dashboard"
import {
  useDashboardBus,
  trackLocalMutation as busTrackLocalMutation,
} from "~/composables/useDashboardBus"
import { useToast } from "~/composables/useToast"
import { useT } from "~/composables/useT"

export interface UseActionStepToggle {
  /** id de l'étape en cours de toggle, null si aucun. */
  pendingId: ComputedRef<string | null>
  /** Marque l'étape comme `done`, gère optimistic + sync EventBus + erreurs. */
  complete: (stepId: string) => Promise<void>
}

interface RuntimeConfigShape {
  public?: { apiBase?: string }
}

export function useActionStepToggle(): UseActionStepToggle {
  const store = useDashboardStore()
  const bus = useDashboardBus()
  const toast = useToast()
  const { t } = useT()
  const pending = ref<string | null>(null)
  // Set sync (hors réactivité Vue) pour anti-double-clic même avant que Vue
  // ne propage la mise à jour de `pending.value` aux observateurs.
  const inFlight = new Set<string>()

  async function complete(stepId: string): Promise<void> {
    if (inFlight.has(stepId)) return
    inFlight.add(stepId)
    pending.value = stepId
    const apiBase =
      (globalThis.useRuntimeConfig?.() as RuntimeConfigShape | undefined)?.public?.apiBase ?? ""
    const url = `${apiBase}/me/action-plan/steps/${stepId}`
    const fetchFn = globalThis.$fetch as
      | (<T>(u: string, o?: Record<string, unknown>) => Promise<T>)
      | undefined
    try {
      if (!fetchFn) throw new Error("$fetch unavailable")
      await fetchFn(url, {
        method: "PATCH",
        body: { status: "done" },
        credentials: "include",
      })
      // Anti-loop : marquer la mutation locale dans le registre bus partagé.
      busTrackLocalMutation(stepId)
      // Émettre event pour synchroniser éventuels autres consommateurs (chat, sidebar).
      bus.emit("action_step:completed", { id: stepId, source: "dashboard" })
      // Invalider + refetch ciblé.
      store.invalidate("next_actions")
      await store.fetchSummary({ scope: ["next_actions"] })
    } catch (_err) {
      toast.push({ severity: "error", message: t("dashboard.action_plan.toggle_error") })
      throw _err
    } finally {
      pending.value = null
      inFlight.delete(stepId)
    }
  }

  return {
    pendingId: computed(() => pending.value),
    complete,
  }
}
