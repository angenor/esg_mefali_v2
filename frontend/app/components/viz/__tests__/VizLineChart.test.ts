// F40 T030 — VizLineChart tests (montage SSR-safe via stubs ClientOnly).
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import VizLineChart from '~/components/viz/VizLineChart.vue'

const SERIES = [
  { label: 'Score E', points: [{ x: 1, y: 10 }, { x: 2, y: 20 }] },
]

describe('VizLineChart', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('rend le titre et le caption', () => {
    const w = mount(VizLineChart, {
      props: { title: 'Trend', caption: 'Mensuel', series: SERIES },
      global: { stubs: { ClientOnly: { template: '<div><slot/></div>' } } },
    })
    expect(w.text()).toContain('Trend')
    expect(w.text()).toContain('Mensuel')
  })

  it('loading masque le canvas', () => {
    const w = mount(VizLineChart, {
      props: { title: 'x', series: SERIES, loading: true },
      global: { stubs: { ClientOnly: { template: '<div><slot/></div>' } } },
    })
    expect(w.find('canvas').exists()).toBe(false)
    expect(w.find('.viz-skeleton').exists()).toBe(true)
  })

  it('empty affiche EmptyState', () => {
    const w = mount(VizLineChart, {
      props: { title: 'x', series: SERIES, empty: true },
      global: { stubs: { ClientOnly: { template: '<div><slot/></div>' } } },
    })
    expect(w.find('.viz-empty').exists()).toBe(true)
  })

  it('aria-label rendu sur le canvas', () => {
    const w = mount(VizLineChart, {
      props: { title: 'Trend', series: SERIES, ariaLabel: 'Mon graphique' },
      global: { stubs: {
        ClientOnly: { template: '<div><slot/></div>' },
        VizChartCanvas: { props: ['ariaLabel'], template: '<canvas :aria-label="ariaLabel"/>' },
      } },
    })
    expect(w.get('canvas').attributes('aria-label')).toBe('Mon graphique')
  })
})
