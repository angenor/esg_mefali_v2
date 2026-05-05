// F38 T024 — Smoke-test layout default
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h } from 'vue'

const NuxtErrorBoundaryStub = defineComponent({
  setup(_, { slots }) {
    return () => h('div', slots.default?.())
  },
})

const loadInitialMock = vi.fn().mockResolvedValue(undefined)
const NuxtLinkStub = defineComponent({
  props: ['to'],
  setup(_, { slots, attrs }) {
    return () => h('a', { ...attrs, href: typeof _.to === 'string' ? _.to : '#' }, slots.default?.())
  },
})

vi.mock('vue-router', async () => {
  const actual = await vi.importActual<typeof import('vue-router')>('vue-router')
  return {
    ...actual,
    useRoute: () => ({ path: '/dashboard', meta: { title: 'Tableau de bord' }, fullPath: '/dashboard' }),
    useRouter: () => ({ afterEach: () => {} }),
  }
})

vi.mock('~/composables/useNotificationsStream', () => ({
  useNotificationsStream: () => ({ start: vi.fn(), stop: vi.fn(), isConnected: { value: false } }),
}))
vi.mock('~/composables/useCommandPalette', () => ({
  useCommandPalette: () => ({
    isOpen: { value: false },
    query: { value: '' },
    actions: { value: new Map() },
    results: { value: [] },
    open: vi.fn(),
    close: vi.fn(),
    toggle: vi.fn(),
    registerActions: vi.fn(),
    unregisterActions: vi.fn(),
  }),
}))
vi.mock('~/stores/auth', () => ({
  useAuthStore: () => ({ user: { email: 'a@b.c' }, logout: vi.fn() }),
}))

;(globalThis as { useNotificationsStore?: unknown }).useNotificationsStore = () => ({
  unreadCount: 0,
  loadInitial: loadInitialMock,
})
;(globalThis as { useHead?: unknown }).useHead = () => {}
;(globalThis as { useAuthStore?: unknown }).useAuthStore = () => ({
  user: { email: 'a@b.c' },
  logout: () => Promise.resolve(),
})

;(window as { matchMedia?: unknown }).matchMedia = vi.fn().mockReturnValue({
  matches: false,
  addEventListener: () => {},
  removeEventListener: () => {},
})

import DefaultLayout from '../../../app/layouts/default.vue'

describe('layouts/default.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    loadInitialMock.mockClear()
  })

  it('compose sidebar + header + main', () => {
    const w = mount(DefaultLayout, {
      slots: { default: '<p data-testid="page">Hello</p>' },
      global: {
        stubs: {
          NuxtErrorBoundary: NuxtErrorBoundaryStub,
          NuxtLink: NuxtLinkStub,
          UiBadge: { template: '<span><slot /></span>' },
          UiTooltip: { template: '<span></span>' },
          ClientOnly: { template: '<div><slot /></div>' },
          Transition: { template: '<div><slot /></div>' },
          TheBottomNav: { template: '<nav data-stub="bottom"></nav>' },
          TheNotificationsBell: { template: '<div data-stub="bell"></div>' },
          TheAvatarMenu: { template: '<div data-stub="avatar"></div>' },
          TheBreadcrumbs: { template: '<nav data-stub="bc"></nav>' },
          TheErrorBoundary: { template: '<div data-stub="eb"></div>' },
          TheCommandPalette: { template: '<div data-stub="palette"></div>' },
          TheBottomNavMore: { template: '<div data-stub="more"></div>' },
        },
      },
    })
    expect(w.find('[data-testid="the-sidebar"]').exists()).toBe(true)
    expect(w.find('[data-testid="the-header"]').exists()).toBe(true)
    expect(w.find('[data-testid="main-content"]').exists()).toBe(true)
    expect(w.html()).toContain('Hello')
  })

  it('appelle loadInitial au montage', async () => {
    mount(DefaultLayout, {
      global: {
        stubs: {
          NuxtErrorBoundary: NuxtErrorBoundaryStub,
          NuxtLink: NuxtLinkStub,
          UiBadge: true,
          UiTooltip: true,
          ClientOnly: { template: '<div><slot /></div>' },
          Transition: { template: '<div><slot /></div>' },
          TheBottomNav: true,
          TheNotificationsBell: true,
          TheAvatarMenu: true,
          TheBreadcrumbs: true,
          TheErrorBoundary: true,
          TheCommandPalette: true,
          TheBottomNavMore: true,
        },
      },
    })
    expect(loadInitialMock).toHaveBeenCalled()
  })
})
