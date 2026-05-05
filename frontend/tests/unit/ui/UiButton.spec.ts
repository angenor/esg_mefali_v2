import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import UiButton from '../../../app/components/ui/UiButton.vue'

describe('UiButton', () => {
  it('renders default variant + size', () => {
    const w = mount(UiButton, { slots: { default: 'Go' } })
    expect(w.text()).toContain('Go')
    expect(w.attributes('data-variant')).toBe('primary')
    expect(w.attributes('data-size')).toBe('md')
    expect(w.attributes('type')).toBe('button')
  })

  it.each(['primary', 'secondary', 'ghost', 'danger', 'link'] as const)(
    'supports variant=%s',
    (variant) => {
      const w = mount(UiButton, { props: { variant } })
      expect(w.attributes('data-variant')).toBe(variant)
    },
  )

  it('emits click', async () => {
    const w = mount(UiButton)
    await w.trigger('click')
    expect(w.emitted('click')).toBeTruthy()
  })

  it('blocks click when disabled', async () => {
    const w = mount(UiButton, { props: { disabled: true } })
    await w.trigger('click')
    expect(w.emitted('click')).toBeFalsy()
  })

  it('blocks click + sets aria-busy when loading', async () => {
    const w = mount(UiButton, { props: { loading: true } })
    expect(w.attributes('aria-busy')).toBe('true')
    await w.trigger('click')
    expect(w.emitted('click')).toBeFalsy()
  })

  it('warns in DEV when iconOnly without ariaLabel', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    mount(UiButton, { props: { iconOnly: true } })
    expect(warn).toHaveBeenCalled()
    warn.mockRestore()
  })

  it('does not warn when iconOnly + ariaLabel', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    mount(UiButton, { props: { iconOnly: true, ariaLabel: 'Fermer' } })
    expect(warn).not.toHaveBeenCalled()
    warn.mockRestore()
  })
})
