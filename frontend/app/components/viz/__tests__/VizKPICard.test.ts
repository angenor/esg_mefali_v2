// F40 T020 — VizKPICard tests.
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import VizKPICard from '~/components/viz/VizKPICard.vue'

describe('VizKPICard', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('rend label, value, unit avec tabular-nums', () => {
    const w = mount(VizKPICard, {
      props: { label: 'Score E', value: 72, unit: '/100' },
    })
    expect(w.text()).toContain('Score E')
    expect(w.text()).toContain('72')
    expect(w.text()).toContain('/100')
    expect(w.find('.viz-kpi__number').classes()).toContain('viz-kpi__number')
  })

  it('delta positif → couleur up + signe +', () => {
    const w = mount(VizKPICard, {
      props: { label: 'Score E', value: 72, delta: 5, deltaUnit: 'pts' },
    })
    const d = w.get('.viz-kpi__delta')
    expect(d.classes()).toContain('viz-kpi__delta--up')
    expect(d.text()).toContain('+5')
    expect(d.text()).toContain('↑')
  })

  it('delta négatif → couleur down + flèche descendante', () => {
    const w = mount(VizKPICard, {
      props: { label: 'Score E', value: 72, delta: -3 },
    })
    const d = w.get('.viz-kpi__delta')
    expect(d.classes()).toContain('viz-kpi__delta--down')
    expect(d.text()).toContain('-3')
    expect(d.text()).toContain('↓')
  })

  it('delta zéro → flat', () => {
    const w = mount(VizKPICard, { props: { label: 'x', value: 0, delta: 0 } })
    expect(w.get('.viz-kpi__delta').classes()).toContain('viz-kpi__delta--flat')
  })

  it('absence de pin sans source_id', () => {
    const w = mount(VizKPICard, { props: { label: 'x', value: 1 } })
    expect(w.find('.viz-source-pin').exists()).toBe(false)
  })

  it('présence du pin avec source_id', () => {
    const w = mount(VizKPICard, { props: { label: 'x', value: 1, source_id: 'src_1' } })
    expect(w.find('.viz-source-pin').exists()).toBe(true)
  })

  it('loading masque la valeur et affiche skeleton', () => {
    const w = mount(VizKPICard, { props: { label: 'x', value: 1, loading: true } })
    expect(w.find('.viz-kpi__number').exists()).toBe(false)
    expect(w.find('.viz-skeleton').exists()).toBe(true)
  })

  it('empty masque la valeur et affiche EmptyState', () => {
    const w = mount(VizKPICard, { props: { label: 'x', value: 1, empty: true } })
    expect(w.find('.viz-kpi__number').exists()).toBe(false)
    expect(w.find('.viz-empty').exists()).toBe(true)
  })

  it('aria-label synthétique généré quand non fourni', () => {
    const w = mount(VizKPICard, {
      props: { label: 'Score', value: 72, unit: '/100', delta: 5 },
    })
    const aria = w.get('article').attributes('aria-label')
    expect(aria).toContain('Score')
    expect(aria).toContain('72')
    expect(aria).toContain('5')
  })

  it('longDescription rend un texte sr-only', () => {
    const w = mount(VizKPICard, {
      props: { label: 'x', value: 1, longDescription: 'description longue' },
    })
    expect(w.html()).toContain('description longue')
    expect(w.find('.sr-only').exists()).toBe(true)
  })
})
