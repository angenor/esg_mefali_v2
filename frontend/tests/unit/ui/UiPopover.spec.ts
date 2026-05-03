import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import UiPopover from '../../../app/components/ui/UiPopover.vue'

describe('UiPopover', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  it('triggerOn=click toggle', async () => {
    const w = mount(UiPopover, {
      slots: { trigger: '<button>T</button>', content: '<p>contenu</p>' },
      attachTo: document.body,
    })
    const trigger = w.find('.ui-popover__trigger')
    await trigger.trigger('click')
    await nextTick()
    expect(document.querySelector('[role="dialog"]')).toBeTruthy()
    expect(w.emitted('update:modelValue')?.[0]).toEqual([true])
    await trigger.trigger('click')
    await nextTick()
    expect(document.querySelector('[role="dialog"]')).toBeNull()
  })

  it('Escape ferme', async () => {
    const w = mount(UiPopover, {
      props: { modelValue: true },
      slots: { trigger: '<button>T</button>', content: '<p>x</p>' },
      attachTo: document.body,
    })
    await nextTick()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await nextTick()
    expect(w.emitted('update:modelValue')?.[0]).toEqual([false])
    expect(w.emitted('close')).toBeTruthy()
  })

  it('click outside ferme', async () => {
    const outside = document.createElement('button')
    document.body.appendChild(outside)
    const w = mount(UiPopover, {
      props: { modelValue: true },
      slots: { trigger: '<button>T</button>', content: '<p>x</p>' },
      attachTo: document.body,
    })
    await nextTick()
    outside.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await nextTick()
    expect(w.emitted('update:modelValue')?.[0]).toEqual([false])
  })

  it('triggerOn=manual : click ne fait rien', async () => {
    const w = mount(UiPopover, {
      props: { triggerOn: 'manual' },
      slots: { trigger: '<button>T</button>', content: '<p>x</p>' },
      attachTo: document.body,
    })
    await w.find('.ui-popover__trigger').trigger('click')
    await nextTick()
    expect(document.querySelector('[role="dialog"]')).toBeNull()
  })

  it('aria-expanded reflète l\'état', async () => {
    const w = mount(UiPopover, {
      slots: { trigger: '<button>T</button>', content: '<p>x</p>' },
      attachTo: document.body,
    })
    const trigger = w.find('.ui-popover__trigger')
    expect(trigger.attributes('aria-expanded')).toBe('false')
    await trigger.trigger('click')
    await nextTick()
    expect(trigger.attributes('aria-expanded')).toBe('true')
  })
})
