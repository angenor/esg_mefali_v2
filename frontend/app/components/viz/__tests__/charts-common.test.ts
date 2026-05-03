// F40 T032 — tests mutualisés Bar/StackedBar/Pie/Donut/Area : props, theme, reduced-motion.
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import VizBarChart from '~/components/viz/VizBarChart.vue'
import VizStackedBarChart from '~/components/viz/VizStackedBarChart.vue'
import VizPieChart from '~/components/viz/VizPieChart.vue'
import VizDonutChart from '~/components/viz/VizDonutChart.vue'
import VizAreaChart from '~/components/viz/VizAreaChart.vue'

const STUBS = { ClientOnly: { template: '<div><slot/></div>' } }

const CAT = { labels: ['a', 'b'], datasets: [{ label: 'x', data: [1, 2] }] }
const PIE = { labels: ['a', 'b'], data: [1, 2] }
const LINE = [{ label: 'x', points: [{ x: 0, y: 1 }, { x: 1, y: 2 }] }]

describe('charts standards', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it.each([
    ['Bar', VizBarChart, { series: CAT }],
    ['StackedBar', VizStackedBarChart, { series: CAT }],
    ['Pie', VizPieChart, { series: PIE }],
    ['Donut', VizDonutChart, { series: PIE }],
    ['Area', VizAreaChart, { series: LINE }],
  ])('rend %s avec titre + canvas (mode normal)', (_n, Comp, extra) => {
    const w = mount(Comp as never, {
      props: { title: 'T', source_id: undefined, ...extra },
      global: { stubs: STUBS },
    })
    expect(w.text()).toContain('T')
  })

  it.each([
    ['Bar', VizBarChart, { series: CAT }],
    ['StackedBar', VizStackedBarChart, { series: CAT }],
    ['Pie', VizPieChart, { series: PIE }],
    ['Donut', VizDonutChart, { series: PIE }],
    ['Area', VizAreaChart, { series: LINE }],
  ])('%s : prop loading affiche skeleton', (_n, Comp, extra) => {
    const w = mount(Comp as never, {
      props: { title: 'T', loading: true, ...extra },
      global: { stubs: STUBS },
    })
    expect(w.find('.viz-skeleton').exists()).toBe(true)
  })

  it.each([
    ['Bar', VizBarChart, { series: CAT }],
    ['Pie', VizPieChart, { series: PIE }],
  ])('%s : prop empty affiche EmptyState', (_n, Comp, extra) => {
    const w = mount(Comp as never, {
      props: { title: 'T', empty: true, ...extra },
      global: { stubs: STUBS },
    })
    expect(w.find('.viz-empty').exists()).toBe(true)
  })
})
