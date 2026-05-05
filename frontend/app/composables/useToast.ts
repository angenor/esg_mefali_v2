import { ref, readonly, type Ref } from 'vue'
import type { UiToast } from '../types/ui'

const MAX_VISIBLE = 5
const DEFAULT_DURATION = 5000

const toasts = ref<UiToast[]>([])
const timers = new Map<string, ReturnType<typeof setTimeout>>()

function schedule(toast: UiToast): void {
  const duration = toast.duration ?? DEFAULT_DURATION
  if (duration <= 0) return
  const t = setTimeout(() => dismiss(toast.id), duration)
  timers.set(toast.id, t)
}

function dismiss(id: string): void {
  const i = toasts.value.findIndex((t) => t.id === id)
  if (i >= 0) toasts.value = toasts.value.filter((t) => t.id !== id)
  const t = timers.get(id)
  if (t) {
    clearTimeout(t)
    timers.delete(id)
  }
}

function clear(): void {
  for (const t of timers.values()) clearTimeout(t)
  timers.clear()
  toasts.value = []
}

let seq = 0
function makeId(): string {
  seq += 1
  return `toast-${Date.now()}-${seq}`
}

export interface UseToastApi {
  toasts: Readonly<Ref<UiToast[]>>
  push: (t: Omit<UiToast, 'id'> & { id?: string }) => string
  dismiss: (id: string) => void
  clear: () => void
}

export function useToast(): UseToastApi {
  return {
    toasts: readonly(toasts),
    push(t) {
      const id = t.id ?? makeId()
      const toast: UiToast = { id, ...t }
      toasts.value = [...toasts.value, toast]
      // FIFO bornée : on retire le plus ancien si > MAX_VISIBLE
      while (toasts.value.length > MAX_VISIBLE) {
        const oldest = toasts.value[0]!
        dismiss(oldest.id)
      }
      schedule(toast)
      return id
    },
    dismiss,
    clear,
  }
}
