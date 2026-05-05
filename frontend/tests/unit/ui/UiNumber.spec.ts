import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiNumber from '../../../app/components/ui/UiNumber.vue'

describe('UiNumber', () => {
  it('emits null when input cleared', async () => {
    const w = mount(UiNumber, { props: { modelValue: 42 } })
    await w.find('input').setValue('')
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual([null])
  })

  it('parses plain numbers', async () => {
    const w = mount(UiNumber)
    await w.find('input').setValue('1234.5')
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual([1234.5])
  })

  it('clamps min/max', async () => {
    const w = mount(UiNumber, { props: { min: 0, max: 100 } })
    await w.find('input').setValue('999')
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual([100])
    await w.find('input').setValue('-5')
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual([0])
  })

  it('mode=money + XOF formats on blur (not focused)', () => {
    const w = mount(UiNumber, {
      props: { modelValue: 12345, mode: 'money', currency: 'XOF' },
    })
    expect(w.find('input').element.value).toMatch(/12[\s  ]?345/)
  })

  it('mode=money + EUR parses comma input', async () => {
    const w = mount(UiNumber, {
      props: { modelValue: null, mode: 'money', currency: 'EUR' },
    })
    const input = w.find('input')
    await input.trigger('focus')
    await input.setValue('1234,5')
    const last = w.emitted('update:modelValue')!.at(-1)![0] as number
    expect(last).toBeCloseTo(1234.5, 2)
  })

  it('inputmode=decimal for mobile', () => {
    const w = mount(UiNumber)
    expect(w.find('input').attributes('inputmode')).toBe('decimal')
  })

  it('focus/blur émettent les events', async () => {
    const w = mount(UiNumber)
    const input = w.find('input')
    await input.trigger('focus')
    await input.trigger('blur')
    expect(w.emitted('focus')).toBeTruthy()
    expect(w.emitted('blur')).toBeTruthy()
  })
})
