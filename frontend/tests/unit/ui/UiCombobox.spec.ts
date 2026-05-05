import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import UiCombobox from '../../../app/components/ui/UiCombobox.vue'

const opts = [
  { value: 'a', label: 'Alpha' },
  { value: 'b', label: 'Bravo' },
  { value: 'c', label: 'Charlie' },
]

describe('UiCombobox', () => {
  it('renders combobox role with aria-expanded', () => {
    const w = mount(UiCombobox, { props: { options: opts } })
    expect(w.find('[role="combobox"]').attributes('aria-expanded')).toBe('false')
  })

  it('opens on input focus + filters locally', async () => {
    const w = mount(UiCombobox, { props: { options: opts } })
    const input = w.find('input')
    await input.trigger('focus')
    await input.setValue('br')
    const visible = w.findAll('[role="option"]')
    expect(visible.length).toBe(1)
    expect(visible[0]!.text()).toContain('Bravo')
  })

  it('emits update:modelValue + select on click', async () => {
    const w = mount(UiCombobox, { props: { options: opts } })
    await w.find('input').trigger('focus')
    await w.findAll('[role="option"]')[0]!.trigger('mousedown')
    expect(w.emitted('update:modelValue')!.at(-1)).toEqual(['a'])
    expect(w.emitted('select')).toBeTruthy()
  })

  it('shows empty slot text when no result', async () => {
    const w = mount(UiCombobox, { props: { options: opts, emptyText: 'Aucun !' } })
    await w.find('input').trigger('focus')
    await w.find('input').setValue('zzz')
    expect(w.text()).toContain('Aucun !')
  })

  it('calls loader and emits reach-end on scroll bottom', async () => {
    const loader = vi
      .fn()
      .mockResolvedValueOnce({ items: opts, total: 6 })
      .mockResolvedValueOnce({ items: opts, total: 6 })
    const w = mount(UiCombobox, { props: { loader } })
    await w.find('input').trigger('focus')
    await flushPromises()
    expect(loader).toHaveBeenCalledTimes(1)
    const list = w.find('[role="listbox"]').element as HTMLElement
    Object.defineProperty(list, 'scrollHeight', { value: 200, configurable: true })
    Object.defineProperty(list, 'clientHeight', { value: 100, configurable: true })
    Object.defineProperty(list, 'scrollTop', { value: 100, configurable: true })
    await w.find('[role="listbox"]').trigger('scroll')
    await flushPromises()
    expect(w.emitted('reach-end')).toBeTruthy()
    expect(loader).toHaveBeenCalledTimes(2)
  })

  it('virtualizes when options > 100', async () => {
    const big = Array.from({ length: 150 }, (_, i) => ({ value: `v${i}`, label: `Label ${i}` }))
    const w = mount(UiCombobox, { props: { options: big } })
    await w.find('input').trigger('focus')
    // Rendu fenêtré → moins d'options DOM que d'items.
    expect(w.findAll('[role="option"]').length).toBeLessThan(big.length)
  })
})
