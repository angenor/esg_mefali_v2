// F52 US2 — Store notificationPreferences (load + togglePreference + flush).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useNotificationPreferencesStore } from '../notificationPreferences'

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

const FIXTURE = {
  items: [
    { kind: 'deadline_j_minus_30', channel: 'email', enabled: true },
    { kind: 'deadline_j_minus_30', channel: 'in_app', enabled: true },
    { kind: 'offre_recommandee', channel: 'email', enabled: true },
    { kind: 'offre_recommandee', channel: 'in_app', enabled: true },
  ],
}

describe('useNotificationPreferencesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: 'http://api' } })
    globalThis.useCsrf = () => ({ withCsrf: () => ({}) })
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('load() peuple les items', async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue(FIXTURE)
    const store = useNotificationPreferencesStore()
    await store.load()
    expect(store.items.length).toBe(4)
  })

  it("togglePreference cumule les patches puis flush après debounce", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(FIXTURE) // load initial
      .mockResolvedValue({ items: [{ kind: 'deadline_j_minus_30', channel: 'email', enabled: false }] })
    globalThis.$fetch = fetchMock
    const store = useNotificationPreferencesStore()
    await store.load()

    store.togglePreference('deadline_j_minus_30', 'email', false)
    store.togglePreference('offre_recommandee', 'email', false)
    expect(store.pendingPatches.length).toBe(2)
    // Avant debounce : pas d'appel HTTP supplémentaire
    expect(fetchMock).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(400)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(store.pendingPatches.length).toBe(0)
  })

  it('isEnabled retourne true par défaut si row inconnue', () => {
    const store = useNotificationPreferencesStore()
    expect(store.isEnabled('system', 'email')).toBe(true)
  })
})
