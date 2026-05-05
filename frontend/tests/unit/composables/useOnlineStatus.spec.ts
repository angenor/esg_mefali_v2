// F38 T008 — Tests useOnlineStatus
import { describe, it, expect, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { useOnlineStatus } from '../../../app/composables/useOnlineStatus'

describe('useOnlineStatus', () => {
  it('reflète navigator.onLine et bascule sur événements online/offline', async () => {
    let api: ReturnType<typeof useOnlineStatus> | null = null
    const Comp = defineComponent({
      setup() {
        api = useOnlineStatus()
        return () => h('div')
      },
    })

    Object.defineProperty(window.navigator, 'onLine', {
      configurable: true,
      get: () => true,
    })
    const w = mount(Comp, { attachTo: document.body })
    await nextTick()
    expect(api!.isOnline.value).toBe(true)

    window.dispatchEvent(new Event('offline'))
    await nextTick()
    expect(api!.isOnline.value).toBe(false)

    window.dispatchEvent(new Event('online'))
    await nextTick()
    expect(api!.isOnline.value).toBe(true)

    w.unmount()
  })

  it('retire les listeners au démontage', async () => {
    const removeSpy = vi.spyOn(window, 'removeEventListener')
    const Comp = defineComponent({
      setup() {
        useOnlineStatus()
        return () => h('div')
      },
    })
    const w = mount(Comp, { attachTo: document.body })
    await nextTick()
    w.unmount()
    expect(removeSpy).toHaveBeenCalledWith('online', expect.any(Function))
    expect(removeSpy).toHaveBeenCalledWith('offline', expect.any(Function))
  })
})
