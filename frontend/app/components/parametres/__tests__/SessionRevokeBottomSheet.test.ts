// F52 US2 — Test SessionRevokeBottomSheet.
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SessionRevokeBottomSheet from '../SessionRevokeBottomSheet.vue'
import { useSessionsStore } from '~/stores/sessions'

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

describe('SessionRevokeBottomSheet', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: 'http://api' } })
    globalThis.useCsrf = () => ({ withCsrf: () => ({}) })
  })

  it('rendu masqué quand sessionId=null', () => {
    const wrapper = mount(SessionRevokeBottomSheet, {
      props: { sessionId: null },
      global: { stubs: { Teleport: true, Transition: true } },
    })
    expect(wrapper.find('[data-testid="session-revoke-confirm"]').exists()).toBe(false)
  })

  it("clique confirm appelle store.revoke et émet close", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue(undefined)
    const wrapper = mount(SessionRevokeBottomSheet, {
      props: { sessionId: 's2' },
      global: { stubs: { Teleport: true, Transition: true } },
    })
    const store = useSessionsStore()
    store.items = [{
      id: 's2',
      device_label: 'PC',
      ip_country: null,
      user_agent_summary: null,
      created_at: '',
      last_seen_at: '',
      is_current: false,
    }]
    await wrapper.get('[data-testid="session-revoke-confirm"]').trigger('click')
    await flushPromises()
    expect(wrapper.emitted('close')).toBeTruthy()
    expect(store.items.find((s) => s.id === 's2')).toBeUndefined()
  })
})
