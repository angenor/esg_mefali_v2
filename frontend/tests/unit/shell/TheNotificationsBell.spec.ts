// F38 T052 — Tests TheNotificationsBell
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h, nextTick } from 'vue'

const navigateToMock = vi.fn(() => Promise.resolve())
;(globalThis as { navigateTo?: unknown }).navigateTo = navigateToMock

const markRead = vi.fn(() => Promise.resolve())
const storeState = {
  unreadCount: 2,
  latestUnread: [
    { id: 'n1', kind: 'system', title: 'Hello', body: 'B1', link: '/projets/1', created_at: 'x', read_at: null },
    { id: 'n2', kind: 'system', title: 'Encore', created_at: 'y', read_at: null },
  ] as unknown[],
  markRead,
}
;(globalThis as { useNotificationsStore?: unknown }).useNotificationsStore = () => storeState

const NuxtLinkStub = defineComponent({
  props: ['to'],
  setup(p, { slots, attrs }) {
    return () => h('a', { ...attrs, href: typeof p.to === 'string' ? p.to : '#' }, slots.default?.())
  },
})

import TheNotificationsBell from '../../../app/components/shell/TheNotificationsBell.vue'

describe('TheNotificationsBell', () => {
  beforeEach(() => {
    navigateToMock.mockClear()
    markRead.mockClear()
  })

  it('badge affiche unreadCount', () => {
    const w = mount(TheNotificationsBell, { global: { stubs: { NuxtLink: NuxtLinkStub } } })
    expect(w.find('[data-testid="bell-badge"]').text()).toBe('2')
  })

  it('clic ouvre le popover', async () => {
    const w = mount(TheNotificationsBell, { global: { stubs: { NuxtLink: NuxtLinkStub } } })
    expect(w.find('[data-testid="bell-popover"]').exists()).toBe(false)
    await w.find('[data-testid="bell-button"]').trigger('click')
    expect(w.find('[data-testid="bell-popover"]').exists()).toBe(true)
  })

  it('clic notif → markRead + navigateTo', async () => {
    const w = mount(TheNotificationsBell, { global: { stubs: { NuxtLink: NuxtLinkStub } } })
    await w.find('[data-testid="bell-button"]').trigger('click')
    await w.find('[data-testid="bell-item-n1"]').trigger('click')
    await flushPromises()
    expect(markRead).toHaveBeenCalledWith('n1')
    expect(navigateToMock).toHaveBeenCalledWith('/projets/1')
  })

  it('Esc ferme le popover', async () => {
    const w = mount(TheNotificationsBell, {
      attachTo: document.body,
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    await w.find('[data-testid="bell-button"]').trigger('click')
    expect(w.find('[data-testid="bell-popover"]').exists()).toBe(true)
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await nextTick()
    expect(w.find('[data-testid="bell-popover"]').exists()).toBe(false)
    w.unmount()
  })
})
