import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiTag from '../../../app/components/ui/UiTag.vue'

describe('UiTag', () => {
  it('rend le contenu', () => {
    const w = mount(UiTag, { slots: { default: 'PME' } })
    expect(w.text()).toContain('PME')
    expect(w.find('button').exists()).toBe(false)
  })

  it('removable rend un bouton avec aria-label par défaut', () => {
    const w = mount(UiTag, { props: { removable: true }, slots: { default: 'X' } })
    const btn = w.find('button')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('aria-label')).toBe('Retirer')
  })

  it('émet remove au clic', async () => {
    const w = mount(UiTag, { props: { removable: true } })
    await w.find('button').trigger('click')
    expect(w.emitted('remove')).toBeTruthy()
  })

  it('émet remove au clavier (Enter/Espace)', async () => {
    const w = mount(UiTag, { props: { removable: true } })
    await w.find('button').trigger('keydown', { key: 'Enter' })
    expect(w.emitted('remove')).toBeTruthy()
  })
})
