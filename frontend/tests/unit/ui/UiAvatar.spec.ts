import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiAvatar from '../../../app/components/ui/UiAvatar.vue'

describe('UiAvatar', () => {
  it('extrait les initiales du nom', () => {
    const w = mount(UiAvatar, { props: { name: 'Aïssatou Diallo' } })
    expect(w.text()).toContain('AD')
  })

  it('? si aucun nom', () => {
    const w = mount(UiAvatar)
    expect(w.text()).toContain('?')
  })

  it('rend l\'image si src présent', () => {
    const w = mount(UiAvatar, { props: { src: 'http://x/y.png', name: 'X' } })
    expect(w.find('img').exists()).toBe(true)
  })

  it('fallback aux initiales si l\'image échoue', async () => {
    const w = mount(UiAvatar, { props: { src: 'http://broken/x.png', name: 'Jean Dupont' } })
    await w.find('img').trigger('error')
    expect(w.find('img').exists()).toBe(false)
    expect(w.text()).toContain('JD')
  })

  it.each(['circle', 'square'] as const)('shape=%s', (s) => {
    const w = mount(UiAvatar, { props: { shape: s, name: 'X' } })
    expect(w.attributes('data-shape')).toBe(s)
  })

  it('aria-label par défaut = name', () => {
    const w = mount(UiAvatar, { props: { name: 'Bintou' } })
    expect(w.attributes('aria-label')).toBe('Bintou')
  })
})
