import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiEmptyState from '../../../app/components/ui/UiEmptyState.vue'

describe('UiEmptyState', () => {
  it('rend les slots illustration / title / description / action', () => {
    const w = mount(UiEmptyState, {
      slots: {
        illustration: '<svg data-testid="illu" />',
        title: 'Aucune donnée',
        description: 'Ajoutez votre premier projet',
        action: '<button>OK</button>',
      },
    })
    expect(w.text()).toContain('Aucune donnée')
    expect(w.text()).toContain('Ajoutez votre premier projet')
    expect(w.text()).toContain('OK')
  })

  it('émet action via actionLabel par défaut', async () => {
    const w = mount(UiEmptyState, { props: { actionLabel: 'Réessayer' } })
    await w.find('button').trigger('click')
    expect(w.emitted('action')).toBeTruthy()
  })

  it('rend props title/description si pas de slot', () => {
    const w = mount(UiEmptyState, { props: { title: 'Vide', description: 'Rien' } })
    expect(w.text()).toContain('Vide')
    expect(w.text()).toContain('Rien')
  })
})
