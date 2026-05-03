import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiTextarea from '../../../app/components/ui/UiTextarea.vue'

describe('UiTextarea', () => {
  it('emits update:modelValue on input', async () => {
    const w = mount(UiTextarea)
    await w.find('textarea').setValue('abc')
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual(['abc'])
  })

  it('honors maxlength', () => {
    const w = mount(UiTextarea, { props: { maxlength: 5 } })
    expect(w.find('textarea').attributes('maxlength')).toBe('5')
  })

  it('shows counter when showCounter + maxlength', () => {
    const w = mount(UiTextarea, { props: { modelValue: 'ab', maxlength: 10, showCounter: true } })
    expect(w.text()).toContain('2/10')
  })

  it('marks aria-invalid + role=alert on error', () => {
    const w = mount(UiTextarea, { props: { error: 'oops' } })
    expect(w.find('textarea').attributes('aria-invalid')).toBe('true')
    expect(w.find('[role="alert"]').text()).toContain('oops')
  })

  it('autosize sets style.height on mount (no crash)', () => {
    const w = mount(UiTextarea, { props: { autosize: true, modelValue: 'multi\nline\ntext' } })
    expect(w.find('textarea').exists()).toBe(true)
  })
})
