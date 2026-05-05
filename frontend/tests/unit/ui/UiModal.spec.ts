import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import UiModal from '../../../app/components/ui/UiModal.vue'

describe('UiModal', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
    ;(globalThis as { __uiModalStack?: number[] }).__uiModalStack = []
  })

  it('rend role=dialog + aria-modal quand ouverte', async () => {
    const w = mount(UiModal, {
      props: { modelValue: true },
      attachTo: document.body,
    })
    await nextTick()
    const dialog = document.querySelector('[role="dialog"]')
    expect(dialog).toBeTruthy()
    expect(dialog?.getAttribute('aria-modal')).toBe('true')
    w.unmount()
  })

  it('ne rend rien quand fermée', async () => {
    mount(UiModal, { props: { modelValue: false }, attachTo: document.body })
    await nextTick()
    expect(document.querySelector('[role="dialog"]')).toBeNull()
  })

  it('Esc ferme la modale par défaut', async () => {
    const w = mount(UiModal, { props: { modelValue: true }, attachTo: document.body })
    await nextTick()
    const evt = new KeyboardEvent('keydown', { key: 'Escape' })
    document.dispatchEvent(evt)
    await nextTick()
    expect(w.emitted('update:modelValue')?.[0]).toEqual([false])
    expect(w.emitted('close')).toBeTruthy()
    w.unmount()
  })

  it('closeOnEsc=false : Esc ne ferme pas', async () => {
    const w = mount(UiModal, {
      props: { modelValue: true, closeOnEsc: false },
      attachTo: document.body,
    })
    await nextTick()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await nextTick()
    expect(w.emitted('update:modelValue')).toBeFalsy()
    w.unmount()
  })

  it('persistent=true : Esc + overlay ne ferment pas', async () => {
    const w = mount(UiModal, {
      props: { modelValue: true, persistent: true },
      attachTo: document.body,
    })
    await nextTick()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await nextTick()
    const overlay = document.querySelector('.ui-modal__overlay') as HTMLElement
    overlay.click()
    await nextTick()
    expect(w.emitted('update:modelValue')).toBeFalsy()
    w.unmount()
  })

  it('click overlay ferme par défaut', async () => {
    const w = mount(UiModal, { props: { modelValue: true }, attachTo: document.body })
    await nextTick()
    const overlay = document.querySelector('.ui-modal__overlay') as HTMLElement
    overlay.click()
    await nextTick()
    expect(w.emitted('update:modelValue')?.[0]).toEqual([false])
    w.unmount()
  })

  it('émet open au montage si modelValue=true', async () => {
    const w = mount(UiModal, { props: { modelValue: true }, attachTo: document.body })
    await nextTick()
    expect(w.emitted('open')).toBeTruthy()
    w.unmount()
  })

  it('empilement : seule la modale au sommet répond à Esc', async () => {
    const a = mount(UiModal, { props: { modelValue: true }, attachTo: document.body })
    await nextTick()
    const b = mount(UiModal, { props: { modelValue: true }, attachTo: document.body })
    await nextTick()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await nextTick()
    expect(a.emitted('update:modelValue')).toBeFalsy()
    expect(b.emitted('update:modelValue')?.[0]).toEqual([false])
    a.unmount()
    b.unmount()
  })

  it('aria-labelledby pointe le header s\'il existe', async () => {
    mount(UiModal, {
      props: { modelValue: true },
      slots: { header: '<h2>Titre</h2>' },
      attachTo: document.body,
    })
    await nextTick()
    const dialog = document.querySelector('[role="dialog"]') as HTMLElement
    const headerId = dialog.getAttribute('aria-labelledby')
    expect(headerId).toBeTruthy()
    expect(document.getElementById(headerId!)?.textContent).toContain('Titre')
  })
})
