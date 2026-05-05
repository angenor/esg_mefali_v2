import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiInput from '../../../app/components/ui/UiInput.vue'

describe('UiInput', () => {
  it('emits update:modelValue on input', async () => {
    const w = mount(UiInput, { props: { modelValue: '' } })
    const input = w.find('input')
    await input.setValue('hello')
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual(['hello'])
  })

  it('honors type prop', () => {
    const w = mount(UiInput, { props: { type: 'email' } })
    expect(w.find('input').attributes('type')).toBe('email')
  })

  it('marks aria-invalid + role=alert when error', () => {
    const w = mount(UiInput, { props: { error: 'Champ requis' } })
    expect(w.find('input').attributes('aria-invalid')).toBe('true')
    expect(w.find('[role="alert"]').text()).toContain('Champ requis')
  })

  it('passes describedby to helper id', () => {
    const w = mount(UiInput, { props: { helper: 'aide', id: 'x1' } })
    expect(w.find('input').attributes('aria-describedby')).toBe('x1-helper')
  })

  it('honors disabled / readonly', () => {
    const w1 = mount(UiInput, { props: { disabled: true } })
    expect(w1.find('input').attributes('disabled')).toBeDefined()
    const w2 = mount(UiInput, { props: { readonly: true } })
    expect(w2.find('input').attributes('readonly')).toBeDefined()
  })

  it('clearable shows × and clears on click', async () => {
    const w = mount(UiInput, { props: { modelValue: 'abc', clearable: true } })
    const btn = w.find('button')
    expect(btn.attributes('aria-label')).toBe('Effacer')
    await btn.trigger('click')
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual([''])
    expect(w.emitted('clear')).toBeTruthy()
  })

  it('change/focus/blur events', async () => {
    const w = mount(UiInput)
    const input = w.find('input')
    await input.trigger('change')
    await input.trigger('focus')
    await input.trigger('blur')
    expect(w.emitted('change')).toBeTruthy()
    expect(w.emitted('focus')).toBeTruthy()
    expect(w.emitted('blur')).toBeTruthy()
  })
})
