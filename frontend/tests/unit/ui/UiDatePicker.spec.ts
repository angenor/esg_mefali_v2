import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiDatePicker from '../../../app/components/ui/UiDatePicker.vue'

// happy-dom normalise <input type="date">. On force la value lue par le handler.
function fireInput(input: HTMLInputElement, v: string): void {
  Object.defineProperty(input, 'value', { value: v, configurable: true })
  input.dispatchEvent(new Event('input', { bubbles: true }))
}

describe('UiDatePicker', () => {
  it('emits ISO yyyy-mm-dd', async () => {
    const w = mount(UiDatePicker)
    fireInput(w.find('input').element as HTMLInputElement, '2026-05-02')
    await w.vm.$nextTick()
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual(['2026-05-02'])
  })

  it('emits null on empty', async () => {
    const w = mount(UiDatePicker, { props: { modelValue: '2026-01-01' } })
    fireInput(w.find('input').element as HTMLInputElement, '')
    await w.vm.$nextTick()
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual([null])
  })

  it('clamps to min', async () => {
    const w = mount(UiDatePicker, { props: { min: '2026-06-01' } })
    fireInput(w.find('input').element as HTMLInputElement, '2026-01-01')
    await w.vm.$nextTick()
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual(['2026-06-01'])
  })

  it('aria-invalid + role=alert on error', () => {
    const w = mount(UiDatePicker, { props: { error: 'oops' } })
    expect(w.find('input').attributes('aria-invalid')).toBe('true')
    expect(w.find('[role="alert"]').exists()).toBe(true)
  })

  it('invalid value does not emit (modelValue preserved)', async () => {
    const w = mount(UiDatePicker, { props: { modelValue: '2026-05-02' } })
    fireInput(w.find('input').element as HTMLInputElement, 'not-a-date')
    await w.vm.$nextTick()
    expect(w.emitted('update:modelValue')).toBeFalsy()
  })
})
