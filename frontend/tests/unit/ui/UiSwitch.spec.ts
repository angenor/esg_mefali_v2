import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiSwitch from '../../../app/components/ui/UiSwitch.vue'

describe('UiSwitch', () => {
  it('rend role=switch + aria-checked false par défaut', () => {
    const w = mount(UiSwitch, { props: { ariaLabel: 'Activer' } })
    expect(w.attributes('role')).toBe('switch')
    expect(w.attributes('aria-checked')).toBe('false')
    expect(w.attributes('aria-label')).toBe('Activer')
  })

  it('toggle au clic', async () => {
    const w = mount(UiSwitch, { props: { ariaLabel: 'X' } })
    await w.trigger('click')
    expect(w.emitted('update:modelValue')?.[0]).toEqual([true])
    expect(w.emitted('change')?.[0]).toEqual([true])
  })

  it('toggle au clavier (Espace)', async () => {
    const w = mount(UiSwitch, { props: { ariaLabel: 'X' } })
    await w.trigger('keydown', { key: ' ' })
    expect(w.emitted('update:modelValue')?.[0]).toEqual([true])
  })

  it('toggle au clavier (Enter)', async () => {
    const w = mount(UiSwitch, { props: { ariaLabel: 'X' } })
    await w.trigger('keydown', { key: 'Enter' })
    expect(w.emitted('update:modelValue')?.[0]).toEqual([true])
  })

  it('aria-checked true quand modelValue=true', () => {
    const w = mount(UiSwitch, { props: { ariaLabel: 'X', modelValue: true } })
    expect(w.attributes('aria-checked')).toBe('true')
  })

  it('disabled : ne toggle pas', async () => {
    const w = mount(UiSwitch, { props: { ariaLabel: 'X', disabled: true } })
    await w.trigger('click')
    expect(w.emitted('update:modelValue')).toBeFalsy()
  })

  it('affiche labelOn quand activé', () => {
    const w = mount(UiSwitch, { props: { ariaLabel: 'X', modelValue: true, labelOn: 'ON' } })
    expect(w.text()).toContain('ON')
  })

  it('affiche labelOff quand désactivé', () => {
    const w = mount(UiSwitch, { props: { ariaLabel: 'X', modelValue: false, labelOff: 'OFF' } })
    expect(w.text()).toContain('OFF')
  })
})
