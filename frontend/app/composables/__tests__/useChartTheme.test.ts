// F40 T013 — useChartTheme tests.
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { useChartTheme } from '~/composables/useChartTheme'

function withTheme(): { theme: ReturnType<typeof useChartTheme> } {
  let captured!: ReturnType<typeof useChartTheme>
  const C = defineComponent({
    setup() {
      captured = useChartTheme()
      return () => h('div')
    },
  })
  mount(C)
  return { theme: captured }
}

describe('useChartTheme', () => {
  beforeEach(() => {
    document.documentElement.style.setProperty('--color-brand-500', '#00ff00')
    document.documentElement.style.setProperty('--color-info-500', '#0011ff')
    document.documentElement.style.setProperty('--color-neutral-200', '#e5e5e5')
  })

  it('lit les CSS variables F36 et expose la palette', () => {
    const { theme } = withTheme()
    expect(theme.value.palette[0]).toMatch(/#00ff00|rgb/i)
    expect(theme.value.palette.length).toBe(6)
    expect(theme.value.grid.color).toMatch(/#e5e5e5|rgb/i)
  })

  it('respecte prefers-reduced-motion = reduce', async () => {
    const original = window.matchMedia
    // @ts-expect-error stub
    window.matchMedia = vi.fn().mockImplementation((q: string) => ({
      matches: q.includes('reduce'),
      media: q,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      onchange: null,
      dispatchEvent: () => false,
    }))
    const { theme } = withTheme()
    await nextTick()
    expect(theme.value.animations.reducedMotion).toBe(true)
    expect(theme.value.animations.duration).toBe(0)
    window.matchMedia = original
  })

  it('fallback si CSS variables absentes', () => {
    document.documentElement.style.removeProperty('--color-brand-500')
    document.documentElement.style.removeProperty('--color-info-500')
    const { theme } = withTheme()
    expect(theme.value.palette.length).toBe(6)
    expect(theme.value.fonts.size).toBe(12)
  })
})
