import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiRadioGroup from '../../../app/components/ui/UiRadioGroup.vue'

const options = [
  { value: 'a', label: 'A' },
  { value: 'b', label: 'B' },
  { value: 'c', label: 'C', disabled: true },
  { value: 'd', label: 'D' },
]

describe('UiRadioGroup', () => {
  it('rend un radiogroup avec layout stacked par défaut', () => {
    const w = mount(UiRadioGroup, { props: { options } })
    expect(w.attributes('role')).toBe('radiogroup')
    expect(w.attributes('data-layout')).toBe('stacked')
    expect(w.findAll('[role="radio"]')).toHaveLength(4)
  })

  it('supporte layout inline', () => {
    const w = mount(UiRadioGroup, { props: { options, layout: 'inline' } })
    expect(w.attributes('data-layout')).toBe('inline')
  })

  it('un seul tabindex=0 (premier non-disabled si pas de selection)', () => {
    const w = mount(UiRadioGroup, { props: { options } })
    const radios = w.findAll('[role="radio"]')
    const tabbable = radios.filter((r) => r.attributes('tabindex') === '0')
    expect(tabbable).toHaveLength(1)
    expect(radios[0]!.attributes('tabindex')).toBe('0')
  })

  it('un seul tabindex=0 sur la valeur sélectionnée', () => {
    const w = mount(UiRadioGroup, { props: { options, modelValue: 'b' } })
    const radios = w.findAll('[role="radio"]')
    expect(radios[0]!.attributes('tabindex')).toBe('-1')
    expect(radios[1]!.attributes('tabindex')).toBe('0')
    expect(radios[1]!.attributes('aria-checked')).toBe('true')
  })

  it('ArrowDown change la sélection et saute les disabled', async () => {
    const w = mount(UiRadioGroup, { props: { options, modelValue: 'b' } })
    const radios = w.findAll('[role="radio"]')
    await radios[1]!.trigger('keydown', { key: 'ArrowDown' })
    // c est disabled → saute à d
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['d'])
  })

  it('ArrowUp wrap au dernier non-disabled', async () => {
    const w = mount(UiRadioGroup, { props: { options, modelValue: 'a' } })
    const radios = w.findAll('[role="radio"]')
    await radios[0]!.trigger('keydown', { key: 'ArrowUp' })
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['d'])
  })

  it('Espace sélectionne le focus courant', async () => {
    const w = mount(UiRadioGroup, { props: { options } })
    const radios = w.findAll('[role="radio"]')
    await radios[0]!.trigger('keydown', { key: ' ' })
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['a'])
    expect(w.emitted('change')?.[0]).toEqual(['a'])
  })

  it('Click sélectionne', async () => {
    const w = mount(UiRadioGroup, { props: { options } })
    const radios = w.findAll('[role="radio"]')
    await radios[1]!.trigger('click')
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['b'])
  })

  it('disabled empêche la sélection', async () => {
    const w = mount(UiRadioGroup, { props: { options, disabled: true } })
    const radios = w.findAll('[role="radio"]')
    await radios[0]!.trigger('click')
    expect(w.emitted('update:modelValue')).toBeFalsy()
  })

  it('Home/End vont aux extrêmes non-disabled', async () => {
    const w = mount(UiRadioGroup, { props: { options, modelValue: 'b' } })
    const radios = w.findAll('[role="radio"]')
    await radios[1]!.trigger('keydown', { key: 'End' })
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['d'])
    await radios[1]!.trigger('keydown', { key: 'Home' })
    expect(w.emitted('update:modelValue')?.[1]).toEqual(['a'])
  })
})
