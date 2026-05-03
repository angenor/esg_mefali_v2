import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiSelect from '../../../app/components/ui/UiSelect.vue'

const opts = [
  { value: 'a', label: 'Alpha' },
  { value: 'b', label: 'Beta', group: 'g1' },
  { value: 'c', label: 'Charlie', group: 'g1' },
]

describe('UiSelect', () => {
  it('renders options', () => {
    const w = mount(UiSelect, { props: { options: opts } })
    expect(w.findAll('option').length).toBeGreaterThanOrEqual(opts.length)
  })

  it('emits update:modelValue + change on select', async () => {
    const w = mount(UiSelect, { props: { options: opts } })
    await w.find('select').setValue('a')
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual(['a'])
    expect(w.emitted('change')).toBeTruthy()
  })

  it('clearable shows placeholder option', () => {
    const w = mount(UiSelect, { props: { options: opts, clearable: true, placeholder: 'Choisir' } })
    expect(w.text()).toContain('Choisir')
  })

  it('emits null when clearing', async () => {
    const w = mount(UiSelect, { props: { options: opts, modelValue: 'a' } })
    await w.find('select').setValue('')
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual([null])
  })

  it('renders groups when groups prop set', () => {
    const w = mount(UiSelect, { props: { options: opts, groups: ['g1'] } })
    expect(w.find('optgroup').exists()).toBe(true)
    expect(w.find('optgroup').attributes('label')).toBe('g1')
  })

  it('aria-invalid when error', () => {
    const w = mount(UiSelect, { props: { options: opts, error: 'oops' } })
    expect(w.find('select').attributes('aria-invalid')).toBe('true')
  })
})
