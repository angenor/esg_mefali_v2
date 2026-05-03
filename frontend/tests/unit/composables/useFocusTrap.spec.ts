import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { ref, nextTick } from 'vue'
import { useFocusTrap } from '../../../app/composables/useFocusTrap'

function buildContainer(html: string): HTMLElement {
  const root = document.createElement('div')
  root.innerHTML = html
  document.body.appendChild(root)
  // happy-dom: stub offsetParent so visibility check passes
  root.querySelectorAll<HTMLElement>('*').forEach((el) => {
    Object.defineProperty(el, 'offsetParent', {
      get() {
        return document.body
      },
      configurable: true,
    })
  })
  return root
}

describe('useFocusTrap', () => {
  let trigger: HTMLButtonElement

  beforeEach(() => {
    trigger = document.createElement('button')
    trigger.textContent = 'trigger'
    document.body.appendChild(trigger)
    trigger.focus()
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('cycles forward on Tab from last to first', async () => {
    const root = buildContainer(
      '<button id="a">A</button><button id="b">B</button><button id="c">C</button>',
    )
    const refEl = ref<HTMLElement | null>(root)
    const trap = useFocusTrap(refEl)
    trap.activate()
    await nextTick()

    const c = root.querySelector<HTMLButtonElement>('#c')!
    c.focus()
    const ev = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true })
    document.dispatchEvent(ev)
    expect(document.activeElement?.id).toBe('a')
    trap.deactivate()
  })

  it('cycles backward on Shift+Tab from first to last', async () => {
    const root = buildContainer('<button id="a">A</button><button id="b">B</button>')
    const refEl = ref<HTMLElement | null>(root)
    const trap = useFocusTrap(refEl)
    trap.activate()
    await nextTick()

    const a = root.querySelector<HTMLButtonElement>('#a')!
    a.focus()
    const ev = new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true })
    document.dispatchEvent(ev)
    expect(document.activeElement?.id).toBe('b')
    trap.deactivate()
  })

  it('restores focus to the previously-focused element on deactivate', async () => {
    const root = buildContainer('<button id="a">A</button>')
    const refEl = ref<HTMLElement | null>(root)
    const trap = useFocusTrap(refEl)
    trap.activate()
    await nextTick()
    expect(document.activeElement?.id).toBe('a')
    trap.deactivate()
    expect(document.activeElement).toBe(trigger)
  })
})
