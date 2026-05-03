import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiMultiSelect from '../../../app/components/ui/UiMultiSelect.vue'

const opts = [
  { value: 'a', label: 'Alpha' },
  { value: 'b', label: 'Bravo' },
  { value: 'c', label: 'Charlie' },
]

describe('UiMultiSelect', () => {
  it('adds an option on click', async () => {
    const w = mount(UiMultiSelect, { props: { options: opts, modelValue: [] } })
    await w.find('input').trigger('focus')
    await w.findAll('[role="option"]')[0]!.trigger('mousedown')
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual([['a']])
  })

  it('removes a chip via × button', async () => {
    const w = mount(UiMultiSelect, { props: { options: opts, modelValue: ['a'] } })
    await w.find('.ui-multi__chip button').trigger('click')
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual([[]])
    expect(w.emitted('remove')).toBeTruthy()
  })

  it('Backspace removes last chip when input empty', async () => {
    const w = mount(UiMultiSelect, { props: { options: opts, modelValue: ['a', 'b'] } })
    await w.find('input').trigger('keydown', { key: 'Backspace' })
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual([['a']])
  })

  it('respects maxSelected', async () => {
    const w = mount(UiMultiSelect, {
      props: { options: opts, modelValue: ['a'], maxSelected: 1 },
    })
    await w.find('input').trigger('focus')
    await w.findAll('[role="option"]')[0]!.trigger('mousedown')
    expect(w.emitted('update:modelValue')).toBeFalsy()
  })

  it('creatable adds free-text on Enter', async () => {
    const w = mount(UiMultiSelect, {
      props: { options: [], modelValue: [], creatable: true },
    })
    const input = w.find('input')
    await input.trigger('focus')
    await input.setValue('libre')
    await input.trigger('keydown', { key: 'Enter' })
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual([['libre']])
  })
})
