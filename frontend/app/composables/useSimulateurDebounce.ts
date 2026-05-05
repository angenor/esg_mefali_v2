// F51 T084 — Debounce 300 ms du simulateur + AbortController.
//
// Wrap autour de useSimulateurStore.compute() pour éviter de spammer le
// backend pendant que l'utilisateur déplace les sliders.

import { onBeforeUnmount } from "vue"
import { useSimulateurStore } from "~/stores/simulateur"

const DEFAULT_DEBOUNCE_MS = 300

export function useSimulateurDebounce(debounceMs: number = DEFAULT_DEBOUNCE_MS) {
  const store = useSimulateurStore()
  let timer: ReturnType<typeof setTimeout> | null = null

  function clearTimer(): void {
    if (timer !== null) {
      clearTimeout(timer)
      timer = null
    }
  }

  function trigger(): void {
    clearTimer()
    timer = setTimeout(() => {
      void store.compute()
    }, debounceMs)
  }

  function flushNow(): Promise<void> {
    clearTimer()
    return store.compute()
  }

  onBeforeUnmount(() => {
    clearTimer()
  })

  return { trigger, flushNow }
}
