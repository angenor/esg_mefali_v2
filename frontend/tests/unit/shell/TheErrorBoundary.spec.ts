// F38 T054 — Tests TheErrorBoundary
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import TheErrorBoundary from '../../../app/components/shell/TheErrorBoundary.vue'

describe('TheErrorBoundary', () => {
  it('rend message FR + role alert', () => {
    const w = mount(TheErrorBoundary, { props: { error: new Error('boom') } })
    expect(w.attributes('role')).toBe('alert')
    expect(w.text()).toContain('Une erreur est survenue')
  })

  it('bouton recharger émet reload', async () => {
    const w = mount(TheErrorBoundary, { props: { error: new Error('boom') } })
    await w.find('[data-testid="error-boundary-reload"]').trigger('click')
    expect(w.emitted('reload')).toBeTruthy()
  })
})
