import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiBadge from '../../../app/components/ui/UiBadge.vue'

describe('UiBadge', () => {
  it('rend severity + variant par défaut', () => {
    const w = mount(UiBadge, { slots: { default: 'NEW' } })
    expect(w.attributes('data-severity')).toBe('info')
    expect(w.attributes('data-variant')).toBe('subtle')
    expect(w.text()).toContain('NEW')
  })

  it.each(['info', 'success', 'warning', 'error'] as const)('severity=%s', (s) => {
    const w = mount(UiBadge, { props: { severity: s } })
    expect(w.attributes('data-severity')).toBe(s)
  })

  it.each(['subtle', 'solid'] as const)('variant=%s', (v) => {
    const w = mount(UiBadge, { props: { variant: v } })
    expect(w.attributes('data-variant')).toBe(v)
  })
})
