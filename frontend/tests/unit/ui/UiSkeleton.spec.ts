import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiSkeleton from '../../../app/components/ui/UiSkeleton.vue'

describe('UiSkeleton', () => {
  it('rend une ligne par défaut', () => {
    const w = mount(UiSkeleton)
    expect(w.attributes('data-shape')).toBe('line')
  })

  it.each(['line', 'rect', 'circle'] as const)('shape=%s', (s) => {
    const w = mount(UiSkeleton, { props: { shape: s } })
    expect(w.find(`[data-shape="${s}"]`).exists()).toBe(true)
  })

  it('lines=3 rend trois éléments', () => {
    const w = mount(UiSkeleton, { props: { shape: 'line', lines: 3 } })
    expect(w.findAll('.ui-skeleton')).toHaveLength(3)
  })

  it('width / height appliqués via inline style', () => {
    const w = mount(UiSkeleton, { props: { shape: 'rect', width: '200px', height: '40px' } })
    const style = w.find('.ui-skeleton').attributes('style') ?? ''
    expect(style).toContain('width: 200px')
    expect(style).toContain('height: 40px')
  })

  it('aria-hidden=true', () => {
    const w = mount(UiSkeleton)
    expect(w.attributes('aria-hidden')).toBe('true')
  })
})
