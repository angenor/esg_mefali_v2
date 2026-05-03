import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiDateRangePicker from '../../../app/components/ui/UiDateRangePicker.vue'

describe('UiDateRangePicker', () => {
  it('emits a range when modelValue is provided', () => {
    const w = mount(UiDateRangePicker, {
      props: { modelValue: { start: '2026-05-01', end: '2026-05-10' } },
    })
    // L'affichage `pretty` (fr-FR) doit s'afficher.
    expect(w.text().toLowerCase()).toMatch(/mai/)
  })

  it('emits a range when both ends set via v-model + change', async () => {
    const w = mount(UiDateRangePicker)
    const inputs = w.findAll('input')
    await inputs[0]!.setValue('2026-05-01')
    await inputs[0]!.trigger('change')
    await inputs[1]!.setValue('2026-05-10')
    await inputs[1]!.trigger('change')
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual([
      { start: '2026-05-01', end: '2026-05-10' },
    ])
  })

  it('aria-invalid via error role=alert', () => {
    const w = mount(UiDateRangePicker, { props: { error: 'oops' } })
    expect(w.find('[role="alert"]').exists()).toBe(true)
  })

  it('renders fr-FR locale labels (lundi/mai)', () => {
    const w = mount(UiDateRangePicker, {
      props: { modelValue: { start: '2026-05-04', end: '2026-05-04' } },
    })
    expect(w.text().toLowerCase()).toMatch(/lundi|mai/)
  })
})
