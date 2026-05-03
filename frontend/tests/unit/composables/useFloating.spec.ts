import { describe, it, expect } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { useFloating } from '../../../app/composables/useFloating'

describe('useFloating', () => {
  it('exposes referenceRef, floatingRef, x/y, placement, update', async () => {
    let api: ReturnType<typeof useFloating> | null = null
    const Comp = defineComponent({
      setup() {
        api = useFloating({ placement: 'top', offsetPx: 8 })
        return () =>
          h('div', [
            h('div', { ref: api!.referenceRef }, 'ref'),
            h('div', { ref: api!.floatingRef, style: api!.floatingStyles.value }, 'float'),
          ])
      },
    })
    mount(Comp, { attachTo: document.body })
    await nextTick()

    expect(api).not.toBeNull()
    expect(api!.referenceRef).toBeDefined()
    expect(api!.floatingRef).toBeDefined()
    expect(typeof api!.update).toBe('function')
    expect(api!.placement.value).toMatch(/top|bottom|left|right/)
  })
})
