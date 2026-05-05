// F38 T010 — Tests useBreadcrumbs
import { describe, it, expect, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'

let mockRoute: { path: string; meta: Record<string, unknown>; params: Record<string, string> }

vi.mock('vue-router', async () => {
  const actual = await vi.importActual<typeof import('vue-router')>('vue-router')
  return {
    ...actual,
    useRoute: () => mockRoute,
  }
})

import { useBreadcrumbs } from '../../../app/composables/useBreadcrumbs'

function harness() {
  let api: ReturnType<typeof useBreadcrumbs> | null = null
  const Comp = defineComponent({
    setup() {
      api = useBreadcrumbs()
      return () => h('div')
    },
  })
  mount(Comp)
  return api!
}

describe('useBreadcrumbs', () => {
  it('retourne fallback Accueil sur route PME sans meta', () => {
    mockRoute = { path: '/dashboard', meta: { layout: 'default' }, params: {} }
    const c = harness()
    expect(c.value).toEqual([{ label: 'Accueil', to: '/dashboard' }])
  })

  it('retourne le tableau meta.breadcrumb tel quel', () => {
    const crumbs = [
      { label: 'Projets', to: '/projets' },
      { label: 'Détail' },
    ]
    mockRoute = { path: '/projets/abc', meta: { breadcrumb: crumbs }, params: {} }
    const c = harness()
    expect(c.value).toEqual(crumbs)
  })

  it('exécute le résolveur fonction', () => {
    const resolver = (r: { params: Record<string, string> }) => [
      { label: 'Projets', to: '/projets' },
      { label: r.params.id },
    ]
    mockRoute = { path: '/projets/xyz', meta: { breadcrumb: resolver }, params: { id: 'xyz' } }
    const c = harness()
    expect(c.value).toEqual([
      { label: 'Projets', to: '/projets' },
      { label: 'xyz' },
    ])
  })

  it('retourne [] sur layout public/auth sans meta', () => {
    mockRoute = { path: '/login', meta: { layout: 'auth' }, params: {} }
    const c = harness()
    expect(c.value).toEqual([])
  })

  it('absorbe une exception du résolveur', () => {
    const bad = () => {
      throw new Error('boom')
    }
    mockRoute = { path: '/x', meta: { breadcrumb: bad }, params: {} }
    const c = harness()
    expect(c.value).toEqual([])
  })
})
