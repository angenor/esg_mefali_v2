import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import UiToast from '../../../app/components/ui/UiToast.vue'
import UiToastHost from '../../../app/components/ui/UiToastHost.vue'
import { useToast } from '../../../app/composables/useToast'

describe('UiToast', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
    vi.useFakeTimers()
    useToast().clear()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('rend role=status pour info', () => {
    const w = mount(UiToast, { props: { id: 't1', severity: 'info', message: 'Hi' } })
    expect(w.attributes('role')).toBe('status')
    expect(w.attributes('aria-live')).toBe('polite')
    expect(w.text()).toContain('Hi')
  })

  it('aria-live=assertive pour error', () => {
    const w = mount(UiToast, { props: { id: 't1', severity: 'error', message: 'Boom' } })
    expect(w.attributes('aria-live')).toBe('assertive')
    expect(w.attributes('role')).toBe('alert')
  })

  it('émet dismiss au clic Fermer', async () => {
    const w = mount(UiToast, { props: { id: 't1', message: 'Hi' } })
    await w.find('button[aria-label="Fermer"]').trigger('click')
    expect(w.emitted('dismiss')?.[0]).toEqual(['t1'])
  })

  it('émet action au clic actionLabel', async () => {
    const w = mount(UiToast, { props: { id: 't1', message: 'Hi', actionLabel: 'Annuler' } })
    await w.find('.ui-toast__action').trigger('click')
    expect(w.emitted('action')?.[0]).toEqual(['t1'])
  })

  it('useToast.push affiche un toast via UiToastHost et auto-dismiss', async () => {
    mount(UiToastHost, { attachTo: document.body })
    const { push, toasts } = useToast()
    push({ severity: 'info', message: 'Sauvegardé', duration: 1000 })
    await nextTick()
    expect(toasts.value.length).toBe(1)
    expect(document.querySelectorAll('.ui-toast').length).toBe(1)
    vi.advanceTimersByTime(1000)
    await nextTick()
    expect(toasts.value.length).toBe(0)
  })

  it('duration=0 → toast persistant', async () => {
    mount(UiToastHost, { attachTo: document.body })
    const { push, toasts } = useToast()
    push({ severity: 'warning', message: 'attention', duration: 0 })
    vi.advanceTimersByTime(60_000)
    await nextTick()
    expect(toasts.value.length).toBe(1)
  })

  it('FIFO bornée à 5 toasts', async () => {
    const { push, toasts } = useToast()
    for (let i = 0; i < 7; i++) push({ severity: 'info', message: `m${i}` })
    expect(toasts.value.length).toBe(5)
    expect(toasts.value[0]!.message).toBe('m2')
  })

  it('pointer events : swipe horizontal au-delà du seuil dismiss', async () => {
    const w = mount(UiToast, { props: { id: 't1', message: 'Hi' } })
    const el = w.element as HTMLElement
    el.setPointerCapture = vi.fn()
    el.dispatchEvent(
      new PointerEvent('pointerdown', { clientX: 0, pointerId: 1, bubbles: true }),
    )
    el.dispatchEvent(new PointerEvent('pointermove', { clientX: 120, bubbles: true }))
    el.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }))
    expect(w.emitted('dismiss')?.[0]).toEqual(['t1'])
  })

  it('pointer events : drag < seuil ne dismiss pas', async () => {
    const w = mount(UiToast, { props: { id: 't1', message: 'Hi' } })
    const el = w.element as HTMLElement
    el.setPointerCapture = vi.fn()
    el.dispatchEvent(
      new PointerEvent('pointerdown', { clientX: 0, pointerId: 1, bubbles: true }),
    )
    el.dispatchEvent(new PointerEvent('pointermove', { clientX: 30, bubbles: true }))
    el.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }))
    expect(w.emitted('dismiss')).toBeFalsy()
  })

  it('UiToastHost déclenche onAction puis dismiss', async () => {
    mount(UiToastHost, { attachTo: document.body })
    const onAction = vi.fn()
    const { push, toasts } = useToast()
    push({ severity: 'info', message: 'X', actionLabel: 'OK', onAction })
    await nextTick()
    const btn = document.querySelector('.ui-toast__action') as HTMLButtonElement
    btn.click()
    await nextTick()
    expect(onAction).toHaveBeenCalled()
    expect(toasts.value.length).toBe(0)
  })

  it('UiToastHost dismiss au clic Fermer', async () => {
    mount(UiToastHost, { attachTo: document.body })
    const { push, toasts } = useToast()
    push({ severity: 'success', message: 'S' })
    await nextTick()
    const close = document.querySelector('.ui-toast__close') as HTMLButtonElement
    close.click()
    await nextTick()
    expect(toasts.value.length).toBe(0)
  })
})
