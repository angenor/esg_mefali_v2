import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiSpinner from '../../../app/components/ui/UiSpinner.vue'

describe('UiSpinner', () => {
  it('role=status + aria-label par défaut FR', () => {
    const w = mount(UiSpinner)
    expect(w.attributes('role')).toBe('status')
    expect(w.attributes('aria-label')).toBe('Chargement…')
  })

  it('label custom', () => {
    const w = mount(UiSpinner, { props: { label: 'Téléversement…' } })
    expect(w.attributes('aria-label')).toBe('Téléversement…')
  })

  it.each(['sm', 'md', 'lg'] as const)('size=%s', (s) => {
    const w = mount(UiSpinner, { props: { size: s } })
    expect(w.attributes('data-size')).toBe(s)
  })
})
