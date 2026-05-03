/**
 * Animation GSAP du bottom sheet — F39.
 * slideUp 200 ms ease-out (NFR-001) / slideDown 160 ms ease-in.
 * Si `prefers-reduced-motion: reduce`, on saute l'animation (durée 0) → FR-017.
 */
import { gsap } from 'gsap'
import { useReducedMotion, gsapDuration } from '~/composables/useReducedMotion'

export interface BottomSheetAnimation {
  slideUp(target: HTMLElement | null): Promise<void>
  slideDown(target: HTMLElement | null): Promise<void>
}

export function useBottomSheetAnimation(): BottomSheetAnimation {
  const reduced = useReducedMotion()

  function slideUp(target: HTMLElement | null): Promise<void> {
    if (!target) return Promise.resolve()
    const duration = gsapDuration(0.2, reduced.value)
    return new Promise<void>((resolve) => {
      gsap.fromTo(
        target,
        { y: '100%', opacity: 0 },
        { y: '0%', opacity: 1, duration, ease: 'power2.out', onComplete: () => resolve() },
      )
    })
  }

  function slideDown(target: HTMLElement | null): Promise<void> {
    if (!target) return Promise.resolve()
    const duration = gsapDuration(0.16, reduced.value)
    return new Promise<void>((resolve) => {
      gsap.to(target, { y: '100%', opacity: 0, duration, ease: 'power2.in', onComplete: () => resolve() })
    })
  }

  return { slideUp, slideDown }
}
