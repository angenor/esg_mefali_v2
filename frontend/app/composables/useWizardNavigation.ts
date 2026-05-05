// F51 T056 — Navigation wizard 5 étapes avec validation par étape.
//
// - Transitions gsap 200 ms (no-op si prefers-reduced-motion).
// - goNext/goPrev/goTo bloquent si la validation locale échoue.
// - validators[step] est une fonction () => boolean | string (true | message d'erreur).

import { computed, ref } from "vue"
import { useReducedMotion } from "~/composables/useReducedMotion"
import type { WizardStepKey } from "~/types/candidatures"

type Validator = () => true | string

interface Options {
  initialStep?: WizardStepKey
  validators?: Partial<Record<WizardStepKey, Validator>>
  onChange?: (step: WizardStepKey) => void
}

export function useWizardNavigation(options: Options = {}) {
  const reduced = useReducedMotion()
  const current = ref<WizardStepKey>(options.initialStep ?? 1)
  const error = ref<string | null>(null)
  const animating = ref(false)

  const validators = options.validators ?? {}

  function validateStep(step: WizardStepKey): true | string {
    const fn = validators[step]
    if (!fn) return true
    return fn()
  }

  async function transition(target: WizardStepKey): Promise<void> {
    if (target === current.value) return
    if (reduced.value) {
      current.value = target
      options.onChange?.(target)
      return
    }
    animating.value = true
    // gsap optionnel via dynamic import (évite hard-dep si non disponible côté tests)
    try {
      const gsap = (await import("gsap")).default ?? (await import("gsap")).gsap
      await new Promise<void>((resolve) => {
        gsap.to(".wizard-step-active", {
          opacity: 0,
          y: -20,
          duration: 0.2,
          onComplete: () => {
            current.value = target
            gsap.fromTo(
              ".wizard-step-active",
              { opacity: 0, y: 20 },
              {
                opacity: 1,
                y: 0,
                duration: 0.2,
                onComplete: () => resolve(),
              },
            )
          },
        })
      })
    } catch {
      current.value = target
    } finally {
      animating.value = false
      options.onChange?.(target)
    }
  }

  async function goNext(): Promise<boolean> {
    error.value = null
    const v = validateStep(current.value)
    if (v !== true) {
      error.value = v
      return false
    }
    const next = (current.value + 1) as WizardStepKey
    if (next > 5) return false
    await transition(next)
    return true
  }

  async function goPrev(): Promise<boolean> {
    error.value = null
    if (current.value === 1) return false
    const prev = (current.value - 1) as WizardStepKey
    await transition(prev)
    return true
  }

  async function goTo(step: WizardStepKey): Promise<boolean> {
    error.value = null
    if (step === current.value) return true
    // Avant de sauter en avant, valider toutes les étapes intermédiaires.
    if (step > current.value) {
      for (let s = current.value; s < step; s++) {
        const v = validateStep(s as WizardStepKey)
        if (v !== true) {
          error.value = v
          return false
        }
      }
    }
    await transition(step)
    return true
  }

  return {
    current: computed(() => current.value),
    error: computed(() => error.value),
    animating: computed(() => animating.value),
    goNext,
    goPrev,
    goTo,
  }
}
