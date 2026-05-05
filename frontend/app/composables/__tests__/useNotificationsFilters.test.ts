// F52 US1 — Tests du composable useNotificationsFilters.
import { describe, expect, it, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useNotificationsStore } from '~/stores/notifications'

// Mocks Nuxt route/router
const routeQuery = { value: {} as Record<string, unknown> }
const replaceCalls: { path?: string; query?: Record<string, string> }[] = []

globalThis.useRoute = () => ({
  path: '/notifications',
  query: routeQuery.value,
})
globalThis.useRouter = () => ({
  replace: (loc: { path?: string; query?: Record<string, string> }) => {
    replaceCalls.push(loc)
    return Promise.resolve(undefined)
  },
})

import { useNotificationsFilters } from '../useNotificationsFilters'

describe('useNotificationsFilters', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    routeQuery.value = {}
    replaceCalls.length = 0
  })

  it('initialise depuis ?unread=1&kind=...', () => {
    routeQuery.value = { unread: '1', kind: 'deadline_j_minus_7,offre_recommandee' }
    useNotificationsFilters(true)
    const store = useNotificationsStore()
    expect(store.filters.unreadOnly).toBe(true)
    expect(store.filters.kinds).toEqual(['deadline_j_minus_7', 'offre_recommandee'])
  })

  it('toggleKind ajoute / retire un kind', () => {
    const { toggleKind } = useNotificationsFilters(true)
    const store = useNotificationsStore()
    toggleKind('deadline_j_minus_30')
    expect(store.filters.kinds).toEqual(['deadline_j_minus_30'])
    toggleKind('deadline_j_minus_30')
    expect(store.filters.kinds).toEqual([])
  })

  it("setUnreadOnly écrit dans la query string", () => {
    const { setUnreadOnly } = useNotificationsFilters(true)
    setUnreadOnly(true)
    expect(replaceCalls.length).toBeGreaterThan(0)
    expect(replaceCalls.at(-1)?.query?.unread).toBe('1')
  })

  it('reset purge filtres et query', () => {
    const { setUnreadOnly, reset } = useNotificationsFilters(true)
    setUnreadOnly(true)
    reset()
    const store = useNotificationsStore()
    expect(store.filters.unreadOnly).toBe(false)
    expect(store.filters.kinds).toEqual([])
  })

  it("filteredItems applique unreadOnly + kinds", () => {
    const store = useNotificationsStore()
    store.items = [
      { id: '1', kind: 'deadline_j_minus_30', title: 'A', created_at: '2026-05-01', read_at: null },
      { id: '2', kind: 'offre_recommandee', title: 'B', created_at: '2026-05-02', read_at: '2026-05-03' },
    ]
    store.setFilters({ unreadOnly: true })
    expect(store.filteredItems.map((n) => n.id)).toEqual(['1'])
    store.setFilters({ unreadOnly: false, kinds: ['offre_recommandee'] })
    expect(store.filteredItems.map((n) => n.id)).toEqual(['2'])
  })
})
