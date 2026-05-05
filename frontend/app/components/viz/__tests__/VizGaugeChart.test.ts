// F40 T040 — VizGaugeChart tests.
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import VizGaugeChart from '~/components/viz/VizGaugeChart.vue'

const STUBS = { ClientOnly: { template: '<div><slot/></div>' } }

describe('VizGaugeChart', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('valeur 68 → zone orange', () => {
    const w = mount(VizGaugeChart, { props: { value: 68 }, global: { stubs: STUBS } })
    expect(w.find('[data-zone="orange"]').exists()).toBe(true)
    expect(w.text()).toContain('68')
  })

  it('valeur 90 → zone green', () => {
    const w = mount(VizGaugeChart, { props: { value: 90 }, global: { stubs: STUBS } })
    expect(w.find('[data-zone="green"]').exists()).toBe(true)
  })

  it('valeur 12 → zone red', () => {
    const w = mount(VizGaugeChart, { props: { value: 12 }, global: { stubs: STUBS } })
    expect(w.find('[data-zone="red"]').exists()).toBe(true)
  })

  it('clamp [min,max]', () => {
    const w = mount(VizGaugeChart, { props: { value: 200 }, global: { stubs: STUBS } })
    expect(w.text()).toContain('100')
  })

  it('aria-label contient la zone', () => {
    const w = mount(VizGaugeChart, { props: { value: 68 }, global: { stubs: STUBS } })
    const aria = w.get('[role="img"]').attributes('aria-label')
    expect(aria).toContain('orange')
  })
})
