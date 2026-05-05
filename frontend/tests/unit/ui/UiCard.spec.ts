import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiCard from '../../../app/components/ui/UiCard.vue'

describe('UiCard', () => {
  it('rend slots header / body / footer', () => {
    const w = mount(UiCard, {
      slots: {
        header: 'Titre',
        default: 'Contenu',
        footer: 'Pied',
      },
    })
    expect(w.text()).toContain('Titre')
    expect(w.text()).toContain('Contenu')
    expect(w.text()).toContain('Pied')
  })

  it('padded par défaut', () => {
    const w = mount(UiCard)
    expect(w.attributes('data-padded')).toBe('true')
  })

  it('elevation appliquée', () => {
    const w = mount(UiCard, { props: { elevation: 'lg' } })
    expect(w.attributes('data-elevation')).toBe('lg')
  })

  it('padded=false retire l\'attribut', () => {
    const w = mount(UiCard, { props: { padded: false } })
    expect(w.attributes('data-padded')).toBeUndefined()
  })
})
