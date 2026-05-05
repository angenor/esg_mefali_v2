import { ref, type Ref } from 'vue'

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

export interface UseFocusTrapOptions {
  initialFocus?: string // CSS selector
  returnFocus?: boolean
}

export interface UseFocusTrapApi {
  active: Ref<boolean>
  activate: () => void
  deactivate: () => void
}

export function useFocusTrap(
  containerRef: Ref<HTMLElement | null>,
  options: UseFocusTrapOptions = {},
): UseFocusTrapApi {
  const active = ref(false)
  let previouslyFocused: HTMLElement | null = null

  function getFocusable(): HTMLElement[] {
    const root = containerRef.value
    if (!root) return []
    return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
      (el) => !el.hasAttribute('inert') && el.offsetParent !== null,
    )
  }

  function onKeydown(e: KeyboardEvent): void {
    if (!active.value || e.key !== 'Tab') return
    const focusable = getFocusable()
    if (focusable.length === 0) {
      e.preventDefault()
      return
    }
    const first = focusable[0]!
    const last = focusable[focusable.length - 1]!
    const current = document.activeElement as HTMLElement | null

    if (e.shiftKey) {
      if (current === first || !containerRef.value?.contains(current)) {
        e.preventDefault()
        last.focus()
      }
    } else {
      if (current === last || !containerRef.value?.contains(current)) {
        e.preventDefault()
        first.focus()
      }
    }
  }

  function activate(): void {
    if (active.value) return
    if (typeof document === 'undefined') return
    previouslyFocused = document.activeElement as HTMLElement | null
    active.value = true
    document.addEventListener('keydown', onKeydown, true)

    // Focus initial
    queueMicrotask(() => {
      const root = containerRef.value
      if (!root) return
      let target: HTMLElement | null = null
      if (options.initialFocus) {
        target = root.querySelector<HTMLElement>(options.initialFocus)
      }
      if (!target) {
        target = getFocusable()[0] ?? root
      }
      target.focus()
    })
  }

  function deactivate(): void {
    if (!active.value) return
    active.value = false
    document.removeEventListener('keydown', onKeydown, true)
    if (options.returnFocus !== false && previouslyFocused) {
      previouslyFocused.focus()
    }
    previouslyFocused = null
  }

  return { active, activate, deactivate }
}
