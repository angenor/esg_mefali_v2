import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiProgress from '../../../app/components/ui/UiProgress.vue'

describe('UiProgress', () => {
  it('rend role=progressbar + ARIA values', () => {
    const w = mount(UiProgress, { props: { modelValue: 42 } })
    expect(w.attributes('role')).toBe('progressbar')
    expect(w.attributes('aria-valuemin')).toBe('0')
    expect(w.attributes('aria-valuemax')).toBe('100')
    expect(w.attributes('aria-valuenow')).toBe('42')
  })

  it('clamp à [0, 100]', () => {
    const w = mount(UiProgress, { props: { modelValue: 250 } })
    expect(w.attributes('aria-valuenow')).toBe('100')
  })

  it.each(['bar', 'circular'] as const)('variant=%s', (v) => {
    const w = mount(UiProgress, { props: { variant: v } })
    expect(w.attributes('data-variant')).toBe(v)
  })

  it('indeterminate retire aria-valuenow', () => {
    const w = mount(UiProgress, { props: { indeterminate: true } })
    expect(w.attributes('data-indeterminate')).toBe('true')
    expect(w.attributes('aria-valuenow')).toBeUndefined()
  })
})
