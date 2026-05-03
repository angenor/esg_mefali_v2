// F38 T055 — Tests TheRouteProgress
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick, ref } from 'vue'

const reduced = ref(false)
vi.mock('~/composables/useReducedMotion', () => ({
  useReducedMotion: () => reduced,
}))

vi.mock('gsap', () => ({ gsap: { to: vi.fn() } }))

const hookHandlers: Record<string, Array<() => void>> = {}
;(globalThis as { useNuxtApp?: unknown }).useNuxtApp = () => ({
  hook: (name: string, cb: () => void) => {
    hookHandlers[name] ??= []
    hookHandlers[name].push(cb)
    return () => {
      hookHandlers[name] = hookHandlers[name]!.filter((h) => h !== cb)
    }
  },
})

import TheRouteProgress from '../../../app/components/shell/TheRouteProgress.vue'

describe('TheRouteProgress', () => {
  beforeEach(() => {
    Object.keys(hookHandlers).forEach((k) => delete hookHandlers[k])
  })

  it('apparaît sur page:start, disparaît après page:finish', async () => {
    vi.useFakeTimers()
    const w = mount(TheRouteProgress)
    expect(w.find('[data-testid="route-progress"]').exists()).toBe(false)

    hookHandlers['page:start']?.forEach((cb) => cb())
    await nextTick()
    expect(w.find('[data-testid="route-progress"]').exists()).toBe(true)

    hookHandlers['page:finish']?.forEach((cb) => cb())
    vi.advanceTimersByTime(400)
    await flushPromises()
    expect(w.find('[data-testid="route-progress"]').exists()).toBe(false)
    vi.useRealTimers()
  })

  it('respecte prefers-reduced-motion (pas de gsap pour scaleX)', async () => {
    reduced.value = true
    const w = mount(TheRouteProgress)
    hookHandlers['page:start']?.forEach((cb) => cb())
    await nextTick()
    const bar = w.find('[data-testid="route-progress"] > div')
    expect(bar.exists()).toBe(true)
    reduced.value = false
  })
})
