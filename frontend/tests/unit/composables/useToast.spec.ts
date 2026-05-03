import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useToast } from '../../../app/composables/useToast'

describe('useToast', () => {
  beforeEach(() => {
    useToast().clear()
    vi.useFakeTimers()
  })

  it('push adds a toast and returns its id', () => {
    const api = useToast()
    const id = api.push({ severity: 'info', message: 'hello' })
    expect(id).toBeTruthy()
    expect(api.toasts.value.length).toBe(1)
  })

  it('auto-dismisses after duration', () => {
    const api = useToast()
    api.push({ severity: 'info', message: 'tick', duration: 1000 })
    expect(api.toasts.value.length).toBe(1)
    vi.advanceTimersByTime(1100)
    expect(api.toasts.value.length).toBe(0)
  })

  it('persists when duration=0', () => {
    const api = useToast()
    api.push({ severity: 'error', message: 'stay', duration: 0 })
    vi.advanceTimersByTime(60000)
    expect(api.toasts.value.length).toBe(1)
  })

  it('caps the queue at 5 toasts (FIFO)', () => {
    const api = useToast()
    for (let i = 0; i < 7; i++) api.push({ severity: 'info', message: `m${i}`, duration: 0 })
    expect(api.toasts.value.length).toBe(5)
    expect(api.toasts.value[0]!.message).toBe('m2')
  })

  it('dismiss removes a specific toast', () => {
    const api = useToast()
    const a = api.push({ severity: 'info', message: 'a', duration: 0 })
    api.push({ severity: 'info', message: 'b', duration: 0 })
    api.dismiss(a)
    expect(api.toasts.value.length).toBe(1)
    expect(api.toasts.value[0]!.message).toBe('b')
  })
})
