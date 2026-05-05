// F42 T030 — Composable de pilotage du tour onboarding (driver.js + fallback mobile)
import { driver, type DriveStep } from "driver.js"
import "driver.js/dist/driver.css"
import { useUserPreferencesStore } from "~/stores/userPreferences"
import { useReducedMotion } from "~/composables/useReducedMotion"
import { useT } from "~/composables/useT"

interface FallbackStep {
  title: string
  body: string
  selector: string
}

interface FullscreenAdapter {
  show(steps: FallbackStep[], handlers: {
    onSkip: () => void
    onDismiss: () => void
    onComplete: () => void
  }): void
  close(): void
}

let fullscreenAdapter: FullscreenAdapter | null = null

export function registerFullscreenAdapter(adapter: FullscreenAdapter): void {
  fullscreenAdapter = adapter
}

function isMobile(): boolean {
  if (typeof window === "undefined") return false
  return window.matchMedia("(max-width: 767px)").matches
}

function buildSteps(t: ReturnType<typeof useT>["t"]): FallbackStep[] {
  return [
    {
      selector: '[data-tour="sidebar"]',
      title: t("onboarding.tour.step.sidebar.title"),
      body: t("onboarding.tour.step.sidebar.body"),
    },
    {
      selector: '[data-tour="profil"]',
      title: t("onboarding.tour.step.profil.title"),
      body: t("onboarding.tour.step.profil.body"),
    },
    {
      selector: '[data-tour="chat"]',
      title: t("onboarding.tour.step.chat.title"),
      body: t("onboarding.tour.step.chat.body"),
    },
    {
      selector: '[data-tour="bibliotheque"]',
      title: t("onboarding.tour.step.bibliotheque.title"),
      body: t("onboarding.tour.step.bibliotheque.body"),
    },
    {
      selector: '[data-tour="plan-action"]',
      title: t("onboarding.tour.step.plan_action.title"),
      body: t("onboarding.tour.step.plan_action.body"),
    },
    {
      selector: '[data-tour="parametres"]',
      title: t("onboarding.tour.step.parametres.title"),
      body: t("onboarding.tour.step.parametres.body"),
    },
  ]
}

export function useOnboardingTour() {
  const prefs = useUserPreferencesStore()
  const reduced = useReducedMotion()
  const { t } = useT()

  let driverInstance: ReturnType<typeof driver> | null = null

  function buildDriverSteps(steps: FallbackStep[]): DriveStep[] {
    return steps
      .filter((s) => typeof document !== "undefined" && document.querySelector(s.selector))
      .map((s) => ({
        element: s.selector,
        popover: {
          title: s.title,
          description: s.body,
          nextBtnText: t("onboarding.tour.next"),
          prevBtnText: t("onboarding.tour.previous"),
          doneBtnText: t("onboarding.tour.finish"),
        },
      }))
  }

  async function safeSet(state: "completed" | "skipped" | "dismissed") {
    try {
      await prefs.set(state)
    } catch {
      // Network failure: ne pas crasher l'UX
    }
  }

  async function complete(): Promise<void> {
    await safeSet("completed")
  }

  async function skip(): Promise<void> {
    await safeSet("skipped")
    driverInstance?.destroy()
    fullscreenAdapter?.close()
  }

  async function dismissForever(): Promise<void> {
    await safeSet("dismissed")
    driverInstance?.destroy()
    fullscreenAdapter?.close()
  }

  async function start(): Promise<void> {
    const steps = buildSteps(t)

    if (isMobile() && fullscreenAdapter) {
      fullscreenAdapter.show(steps, {
        onSkip: () => void skip(),
        onDismiss: () => void dismissForever(),
        onComplete: () => void complete(),
      })
      return
    }

    const driverSteps = buildDriverSteps(steps)
    if (driverSteps.length === 0) {
      // Aucun sélecteur trouvé : marquer skipped pour ne pas boucler
      await skip()
      return
    }

    driverInstance = driver({
      animate: !reduced.value,
      stagePadding: reduced.value ? 0 : 8,
      showProgress: true,
      steps: driverSteps,
      onDestroyStarted: () => {
        // L'utilisateur a fermé via X / outside / ESC : considère skipped
        if (driverInstance && !driverInstance.isLastStep()) {
          void skip()
        } else {
          void complete()
        }
        driverInstance?.destroy()
      },
    })
    driverInstance.drive()
  }

  async function startIfPending(): Promise<void> {
    if (!prefs.loaded) {
      try {
        await prefs.load()
      } catch {
        return
      }
    }
    if (prefs.state !== "pending") return
    await start()
  }

  return { startIfPending, start, skip, dismissForever, complete }
}
