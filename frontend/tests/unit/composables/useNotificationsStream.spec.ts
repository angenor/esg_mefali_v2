// F38 T051 — Tests useNotificationsStream
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

class FakeEventSource {
  static instances: FakeEventSource[] = []
  url: string
  listeners: Record<string, Array<(ev: unknown) => void>> = {}
  closed = false
  constructor(url: string) {
    this.url = url
    FakeEventSource.instances.push(this)
  }
  addEventListener(name: string, cb: (ev: unknown) => void): void {
    this.listeners[name] ??= []
    this.listeners[name].push(cb)
  }
  dispatch(name: string, ev?: unknown): void {
    ;(this.listeners[name] ?? []).forEach((cb) => cb(ev))
  }
  close(): void {
    this.closed = true
  }
}

;(globalThis as { useRuntimeConfig?: unknown }).useRuntimeConfig = () => ({
  public: { apiBase: 'http://api.test' },
})

const loadInitialMock = vi.fn()
const setConnectedMock = vi.fn()
vi.mock('~/stores/notifications', () => ({
  useNotificationsStore: () => ({
    loadInitial: loadInitialMock,
    setStreamConnected: setConnectedMock,
    pushFromStream: vi.fn(),
  }),
}))

import { __resetNotificationsStream, useNotificationsStream } from '../../../app/composables/useNotificationsStream'

describe('useNotificationsStream', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    __resetNotificationsStream()
    FakeEventSource.instances = []
    ;(globalThis as { EventSource?: unknown }).EventSource = FakeEventSource
    loadInitialMock.mockClear()
    setConnectedMock.mockClear()
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('start ouvre une EventSource', () => {
    const s = useNotificationsStream()
    s.start()
    expect(FakeEventSource.instances.length).toBe(1)
    expect(FakeEventSource.instances[0]!.url).toContain('/me/events')
  })

  it('open marque connecté', () => {
    const s = useNotificationsStream()
    s.start()
    FakeEventSource.instances[0]!.dispatch('open')
    expect(s.isConnected.value).toBe(true)
    expect(setConnectedMock).toHaveBeenCalledWith(true)
  })

  it('error → fallback polling et reconnexion programmée', () => {
    const s = useNotificationsStream()
    s.start()
    FakeEventSource.instances[0]!.dispatch('error')
    expect(FakeEventSource.instances[0]!.closed).toBe(true)
    // Polling déclenché : avancer de 60s pour invoquer setInterval callback
    vi.advanceTimersByTime(60_000)
    expect(loadInitialMock).toHaveBeenCalled()
    // Reconnexion : avance jusqu'au 1er backoff (1s)
    vi.advanceTimersByTime(1000)
    expect(FakeEventSource.instances.length).toBe(2)
  })

  it('stop ferme la connexion et clear interval', () => {
    const s = useNotificationsStream()
    s.start()
    s.stop()
    expect(FakeEventSource.instances[0]!.closed).toBe(true)
    expect(s.isConnected.value).toBe(false)
  })
})
