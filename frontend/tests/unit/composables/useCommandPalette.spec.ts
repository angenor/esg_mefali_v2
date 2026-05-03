// F38 T032 — Tests useCommandPalette
import { describe, it, expect, beforeEach } from 'vitest'
import {
  useCommandPalette,
  __resetCommandPalette,
  type CommandAction,
} from '../../../app/composables/useCommandPalette'

function action(overrides: Partial<CommandAction>): CommandAction {
  return {
    id: 'x',
    label: 'X',
    group: 'Navigation',
    ...overrides,
  }
}

describe('useCommandPalette', () => {
  beforeEach(() => {
    __resetCommandPalette()
  })

  it('expose un singleton (deux appels = même état)', () => {
    const a = useCommandPalette()
    const b = useCommandPalette()
    a.open()
    expect(b.isOpen.value).toBe(true)
  })

  it('open/close/toggle', () => {
    const p = useCommandPalette()
    expect(p.isOpen.value).toBe(false)
    p.open()
    expect(p.isOpen.value).toBe(true)
    p.close()
    expect(p.isOpen.value).toBe(false)
    p.toggle()
    expect(p.isOpen.value).toBe(true)
    p.toggle()
    expect(p.isOpen.value).toBe(false)
  })

  it('close vide la query', () => {
    const p = useCommandPalette()
    p.open()
    p.query.value = 'scoring'
    p.close()
    expect(p.query.value).toBe('')
  })

  it('registerActions dédoublonne par id', () => {
    const p = useCommandPalette()
    p.registerActions([action({ id: 'a', label: 'A' }), action({ id: 'a', label: 'A bis' })])
    p.registerActions([action({ id: 'a', label: 'A ter' })])
    expect(p.actions.value.size).toBe(1)
    expect(p.actions.value.get('a')?.label).toBe('A ter')
  })

  it('unregisterActions retire par id', () => {
    const p = useCommandPalette()
    p.registerActions([action({ id: 'a' }), action({ id: 'b' })])
    p.unregisterActions(['a'])
    expect(p.actions.value.has('a')).toBe(false)
    expect(p.actions.value.has('b')).toBe(true)
  })

  it('filtre tolère les accents (NFD)', () => {
    const p = useCommandPalette()
    p.registerActions([action({ id: 'p1', label: 'Paramètres' })])
    p.query.value = 'parametres'
    expect(p.results.value.map((r) => r.id)).toContain('p1')
  })

  it('classe préfixe avant substring avant keywords', () => {
    const p = useCommandPalette()
    p.registerActions([
      action({ id: 'sub', label: 'Voir le scoring' }), // substring
      action({ id: 'pref', label: 'Scoring ESG' }), // préfixe
      action({ id: 'kw', label: 'Tableau de bord', keywords: ['scoring'] }),
    ])
    p.query.value = 'scoring'
    const ids = p.results.value.map((r) => r.id)
    expect(ids[0]).toBe('pref')
    expect(ids[1]).toBe('sub')
    expect(ids[2]).toBe('kw')
  })

  it('plafonne à 20 résultats', () => {
    const p = useCommandPalette()
    p.registerActions(
      Array.from({ length: 30 }, (_, i) => action({ id: `n${i}`, label: `Nav ${i}` }))
    )
    p.query.value = 'nav'
    expect(p.results.value.length).toBe(20)
  })

  it('query vide retourne toutes les actions enregistrées (≤ 20)', () => {
    const p = useCommandPalette()
    p.registerActions([action({ id: 'a' }), action({ id: 'b' })])
    p.query.value = ''
    expect(p.results.value.length).toBe(2)
  })
})
