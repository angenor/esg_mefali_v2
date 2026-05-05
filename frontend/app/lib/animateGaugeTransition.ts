/**
 * F48 — Tween gsap entre deux valeurs de score crédit (0..100).
 *
 * Respecte `prefers-reduced-motion` : applique la valeur finale instantanément.
 * Annule toute tween en cours sur le même élément avant d'en démarrer une nouvelle.
 */

import { gsap } from 'gsap'

export interface AnimateGaugeOptions {
  duration?: number
  reducedMotion?: boolean
  onUpdate?: (value: number) => void
  onComplete?: () => void
}

const DEFAULT_DURATION_S = 0.32

export function animateGaugeTransition(
  target: { value: number } | HTMLElement | SVGElement,
  fromScore: number,
  toScore: number,
  options: AnimateGaugeOptions = {},
): gsap.core.Tween | null {
  const {
    duration = DEFAULT_DURATION_S,
    reducedMotion = false,
    onUpdate,
    onComplete,
  } = options

  const proxy = isPlainTarget(target) ? target : { value: fromScore }

  if (reducedMotion) {
    proxy.value = toScore
    onUpdate?.(toScore)
    onComplete?.()
    return null
  }

  // Annule les tweens existants sur ce proxy.
  gsap.killTweensOf(proxy)
  proxy.value = fromScore

  return gsap.to(proxy, {
    value: toScore,
    duration,
    ease: 'power2.out',
    onUpdate: () => onUpdate?.(proxy.value),
    onComplete,
  })
}

function isPlainTarget(t: unknown): t is { value: number } {
  return (
    typeof t === 'object'
    && t !== null
    && 'value' in (t as Record<string, unknown>)
    && typeof (t as { value: unknown }).value === 'number'
  )
}
