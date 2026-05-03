// F40 T031 — VizRadarChart tests (cap 6 axes).
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import VizRadarChart from '~/components/viz/VizRadarChart.vue'

const STUBS = { ClientOnly: { template: '<div><slot/></div>' } }

describe('VizRadarChart', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('warn console si > 6 axes et tronque à 6', () => {
    const spy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const series = {
      axes: ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'],
      datasets: [{ label: 'x', data: [1, 2, 3, 4, 5, 6, 7, 8] }],
    }
    mount(VizRadarChart, { props: { title: 'r', series }, global: { stubs: STUBS } })
    expect(spy).toHaveBeenCalled()
    spy.mockRestore()
  })

  it('aucun warning si ≤ 6 axes', () => {
    const spy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const series = {
      axes: ['a', 'b', 'c'],
      datasets: [{ label: 'x', data: [1, 2, 3] }],
    }
    mount(VizRadarChart, { props: { title: 'r', series }, global: { stubs: STUBS } })
    expect(spy).not.toHaveBeenCalled()
    spy.mockRestore()
  })
})
