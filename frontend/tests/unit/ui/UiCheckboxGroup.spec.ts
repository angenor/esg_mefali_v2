import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiCheckboxGroup from '../../../app/components/ui/UiCheckboxGroup.vue'

const options = [
  { value: 'a', label: 'A' },
  { value: 'b', label: 'B' },
  { value: 'c', label: 'C', disabled: true },
]

describe('UiCheckboxGroup', () => {
  it('rend un fieldset avec layout stacked par défaut', () => {
    const w = mount(UiCheckboxGroup, { props: { options } })
    expect(w.element.tagName).toBe('FIELDSET')
    expect(w.attributes('data-layout')).toBe('stacked')
    expect(w.findAll('input[type="checkbox"]')).toHaveLength(3)
  })

  it('layout inline', () => {
    const w = mount(UiCheckboxGroup, { props: { options, layout: 'inline' } })
    expect(w.attributes('data-layout')).toBe('inline')
  })

  it('v-model array : ajoute la valeur cliquée', async () => {
    const w = mount(UiCheckboxGroup, { props: { options, modelValue: [] } })
    await w.findAll('input')[0]!.setValue(true)
    expect(w.emitted('update:modelValue')?.[0]).toEqual([['a']])
  })

  it('v-model array : retire la valeur si déjà cochée', async () => {
    const w = mount(UiCheckboxGroup, { props: { options, modelValue: ['a', 'b'] } })
    await w.findAll('input')[0]!.setValue(false)
    expect(w.emitted('update:modelValue')?.[0]).toEqual([['b']])
  })

  it('option disabled empêche le toggle', async () => {
    const w = mount(UiCheckboxGroup, { props: { options, modelValue: [] } })
    const cInput = w.findAll('input')[2]!
    expect(cInput.attributes('disabled')).toBeDefined()
  })

  it('disabled global empêche tout toggle', async () => {
    const w = mount(UiCheckboxGroup, { props: { options, modelValue: [], disabled: true } })
    for (const input of w.findAll('input')) {
      expect(input.attributes('disabled')).toBeDefined()
    }
  })

  it('aria-checked reflète la sélection', () => {
    const w = mount(UiCheckboxGroup, { props: { options, modelValue: ['b'] } })
    const inputs = w.findAll('input')
    expect(inputs[0]!.attributes('aria-checked')).toBe('false')
    expect(inputs[1]!.attributes('aria-checked')).toBe('true')
  })
})
