import { useFloating as useFloatingUi, autoUpdate, flip, offset, shift } from '@floating-ui/vue'
import type { Placement, Strategy } from '@floating-ui/vue'
import { ref, type Ref } from 'vue'

export interface UseFloatingOptions {
  placement?: Placement
  strategy?: Strategy
  offsetPx?: number
  open?: Ref<boolean>
}

// Wrapper typé sur @floating-ui/vue (R-002).
export function useFloating(options: UseFloatingOptions = {}) {
  const referenceRef = ref<HTMLElement | null>(null)
  const floatingRef = ref<HTMLElement | null>(null)

  const result = useFloatingUi(referenceRef, floatingRef, {
    placement: options.placement ?? 'bottom-start',
    strategy: options.strategy ?? 'absolute',
    middleware: [offset(options.offsetPx ?? 4), flip(), shift({ padding: 8 })],
    whileElementsMounted: autoUpdate,
    open: options.open,
  })

  return {
    referenceRef,
    floatingRef,
    x: result.x,
    y: result.y,
    strategy: result.strategy,
    placement: result.placement,
    update: result.update,
    floatingStyles: result.floatingStyles,
  }
}
