import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import UiTooltip from '../../../app/components/ui/UiTooltip.vue'

describe('UiTooltip', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    document.body.innerHTML = ''
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('ne rend pas le tooltip avant hover', async () => {
    mount(UiTooltip, {
      slots: { default: '<button>Trigger</button>', content: 'Aide' },
      attachTo: document.body,
    })
    await nextTick()
    expect(document.querySelector('[role="tooltip"]')).toBeNull()
  })

  it('open au mouseenter après delay', async () => {
    const w = mount(UiTooltip, {
      props: { delay: 100 },
      slots: { default: '<button>Trigger</button>', content: 'Aide' },
      attachTo: document.body,
    })
    await w.trigger('mouseenter')
    vi.advanceTimersByTime(100)
    await nextTick()
    expect(document.querySelector('[role="tooltip"]')).toBeTruthy()
    expect(w.emitted('open')).toBeTruthy()
  })

  it('close au mouseleave', async () => {
    const w = mount(UiTooltip, {
      props: { delay: 0 },
      slots: { default: '<button>X</button>', content: 'Aide' },
      attachTo: document.body,
    })
    await w.trigger('mouseenter')
    vi.advanceTimersByTime(0)
    await nextTick()
    await w.trigger('mouseleave')
    vi.advanceTimersByTime(100)
    await nextTick()
    expect(document.querySelector('[role="tooltip"]')).toBeNull()
    expect(w.emitted('close')).toBeTruthy()
  })

  it('open au focusin', async () => {
    const w = mount(UiTooltip, {
      props: { delay: 0 },
      slots: { default: '<button>X</button>', content: 'Aide' },
      attachTo: document.body,
    })
    await w.trigger('focusin')
    vi.advanceTimersByTime(0)
    await nextTick()
    expect(document.querySelector('[role="tooltip"]')).toBeTruthy()
  })

  it('disabled : pas d\'ouverture', async () => {
    const w = mount(UiTooltip, {
      props: { delay: 0, disabled: true },
      slots: { default: '<button>X</button>', content: 'Aide' },
      attachTo: document.body,
    })
    await w.trigger('mouseenter')
    vi.advanceTimersByTime(100)
    await nextTick()
    expect(document.querySelector('[role="tooltip"]')).toBeNull()
  })
})
