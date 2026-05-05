// F38 T074 — Audit a11y (axe-core) sur les 3 layouts.
// Smoke-test : aucun violation level A/AA sur le HTML rendu (jsdom).
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h } from 'vue'
import axe from 'axe-core'

const NuxtErrorBoundaryStub = defineComponent({
  setup(_, { slots }) {
    return () => h('div', slots.default?.())
  },
})
const NuxtLinkStub = defineComponent({
  props: ['to'],
  setup(props, { slots, attrs }) {
    return () =>
      h('a', { ...attrs, href: typeof props.to === 'string' ? props.to : '#' }, slots.default?.())
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
  loadInitial: vi.fn().mockResolvedValue(undefined),
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
import PublicLayout from '../../../app/layouts/public.vue'
import AuthLayout from '../../../app/layouts/auth.vue'

const SHARED_STUBS = {
  NuxtErrorBoundary: NuxtErrorBoundaryStub,
  NuxtLink: NuxtLinkStub,
  UiBadge: { template: '<span><slot /></span>' },
  UiTooltip: { template: '<span><slot /></span>' },
  ClientOnly: { template: '<div><slot /></div>' },
  Transition: { template: '<div><slot /></div>' },
  TheBottomNav: { template: '<nav aria-label="Navigation principale"></nav>' },
  TheNotificationsBell: { template: '<div></div>' },
  TheAvatarMenu: { template: '<div></div>' },
  TheBreadcrumbs: { template: '<nav aria-label="Fil d\'Ariane"></nav>' },
  TheErrorBoundary: { template: '<div><slot /></div>' },
  TheCommandPalette: { template: '<div></div>' },
  TheBottomNavMore: { template: '<div></div>' },
}

async function runAxe(html: string): Promise<axe.AxeResults> {
  const container = document.createElement('div')
  // Wrap dans un document complet : axe exige <html> + <body> avec lang.
  container.innerHTML = html
  document.body.appendChild(container)
  document.documentElement.lang = 'fr'
  try {
    return await axe.run(container, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
      // Désactive les règles dépendantes du contexte page complète (couleur, region) :
      // les layouts sont testés en isolation (pas de viewport, pas de palette CSS hydratée).
      rules: {
        'color-contrast': { enabled: false },
        region: { enabled: false },
        'landmark-one-main': { enabled: false },
      },
    })
  } finally {
    document.body.removeChild(container)
  }
}

describe('a11y — layouts du shell (axe-core, WCAG 2.1 A/AA)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('layouts/default.vue n\'a pas de violations critiques', async () => {
    const w = mount(DefaultLayout, {
      slots: { default: '<p>Contenu</p>' },
      global: { stubs: SHARED_STUBS },
    })
    const results = await runAxe(w.html())
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([])
  })

  it('layouts/public.vue n\'a pas de violations critiques', async () => {
    const w = mount(PublicLayout, {
      slots: { default: '<p>Contenu public</p>' },
      global: { stubs: SHARED_STUBS },
    })
    const results = await runAxe(w.html())
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([])
  })

  it('layouts/auth.vue n\'a pas de violations critiques', async () => {
    const w = mount(AuthLayout, {
      slots: { default: '<form><label for="e">Email</label><input id="e" type="email"/></form>' },
      global: { stubs: SHARED_STUBS },
    })
    const results = await runAxe(w.html())
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([])
  })
})
