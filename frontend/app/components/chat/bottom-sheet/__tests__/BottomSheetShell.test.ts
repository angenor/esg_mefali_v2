import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import BottomSheetShell from '../BottomSheetShell.vue'

vi.mock('gsap', () => {
  const noop = (_target: unknown, opts: { onComplete?: () => void } = {}) => {
    opts.onComplete?.()
    return { kill: () => {} }
  }
  return {
    gsap: { fromTo: (_t: unknown, _f: unknown, opts: { onComplete?: () => void } = {}) => noop(null, opts), to: noop },
    default: { fromTo: () => {}, to: () => {} },
  }
})

describe('BottomSheetShell', () => {
  it('rend le titre avec aria-modal', async () => {
    const wrapper = mount(BottomSheetShell, { props: { title: 'Question ?' }, attachTo: document.body })
    await nextTick()
    const dialog = wrapper.find('[role="dialog"]')
    expect(dialog.exists()).toBe(true)
    expect(dialog.attributes('aria-modal')).toBe('true')
    expect(wrapper.text()).toContain('Question ?')
    wrapper.unmount()
  })

  it('émet dismiss-for-freetext sur clic du bouton « Répondre librement »', async () => {
    const wrapper = mount(BottomSheetShell, { props: { title: 'T' }, attachTo: document.body })
    await nextTick()
    await wrapper.find('[data-testid="chat-bottom-sheet-freetext"]').trigger('click')
    expect(wrapper.emitted('dismiss-for-freetext')).toBeTruthy()
    wrapper.unmount()
  })

  it('émet dismiss-for-freetext sur ESC (sauf inFlight)', async () => {
    const wrapper = mount(BottomSheetShell, { props: { title: 'T' }, attachTo: document.body })
    await nextTick()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await nextTick()
    expect(wrapper.emitted('dismiss-for-freetext')).toBeTruthy()
    wrapper.unmount()
  })

  it('ne ferme pas sur ESC pendant inFlight', async () => {
    const wrapper = mount(BottomSheetShell, { props: { title: 'T', inFlight: true }, attachTo: document.body })
    await nextTick()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await nextTick()
    expect(wrapper.emitted('dismiss-for-freetext')).toBeFalsy()
    wrapper.unmount()
  })

  it('émet submit quand bouton Valider cliqué et non disabled', async () => {
    const wrapper = mount(BottomSheetShell, { props: { title: 'T' }, attachTo: document.body })
    await nextTick()
    await wrapper.find('[data-testid="chat-bottom-sheet-submit"]').trigger('click')
    expect(wrapper.emitted('submit')).toBeTruthy()
    wrapper.unmount()
  })

  it('bloque submit quand submitDisabled=true', async () => {
    const wrapper = mount(BottomSheetShell, { props: { title: 'T', submitDisabled: true }, attachTo: document.body })
    await nextTick()
    const btn = wrapper.find('[data-testid="chat-bottom-sheet-submit"]')
    expect((btn.element as HTMLButtonElement).disabled).toBe(true)
    await btn.trigger('click')
    expect(wrapper.emitted('submit')).toBeFalsy()
    wrapper.unmount()
  })
})
