// F40 T007 — moneyFormat tests (P5 / SC-009).
import { describe, it, expect } from 'vitest'
import { formatMoney, isMoneyValue } from '~/utils/moneyFormat'

describe('formatMoney', () => {
  it('formate XOF sans décimales en fr-FR', () => {
    const out = formatMoney({ amount: '1500000', currency: 'XOF' })
    // Intl renvoie un espace insécable — on vérifie la substance
    expect(out).toMatch(/1\s?500\s?000/)
    // Intl peut afficher "XOF" ou "F CFA" selon ICU — les deux sont valides
    expect(out).toMatch(/XOF|F\s?CFA/)
  })

  it('formate EUR avec 2 décimales', () => {
    const out = formatMoney({ amount: '1234.56', currency: 'EUR' })
    expect(out).toContain('1')
    expect(out).toContain('234')
    expect(out).toContain('56')
    expect(out).toMatch(/€/)
  })

  it('formate USD avec 2 décimales en fr-FR', () => {
    const out = formatMoney({ amount: '999.5', currency: 'USD' })
    expect(out).toContain('999')
    expect(out).toContain('50')
  })

  it('renvoie -- si amount n\'est pas une chaîne valide', () => {
    expect(formatMoney({ amount: '', currency: 'EUR' })).toBe('--')
    expect(formatMoney({ amount: 'abc', currency: 'EUR' })).toBe('--')
    // @ts-expect-error vérification runtime
    expect(formatMoney({ amount: 1234, currency: 'EUR' })).toBe('--')
  })

  it('renvoie -- si la valeur est null ou mal typée', () => {
    // @ts-expect-error null guard
    expect(formatMoney(null)).toBe('--')
    // @ts-expect-error missing currency
    expect(formatMoney({ amount: '10' })).toBe('--')
  })

  it('formate un montant Decimal très grand (BigInt path)', () => {
    const out = formatMoney({ amount: '12345678901234567890.55', currency: 'EUR' })
    expect(out).toMatch(/€/)
    expect(out.length).toBeGreaterThan(15)
  })

  it('isMoneyValue valide les bonnes formes uniquement', () => {
    expect(isMoneyValue({ amount: '10', currency: 'EUR' })).toBe(true)
    expect(isMoneyValue({ amount: 10, currency: 'EUR' })).toBe(false)
    expect(isMoneyValue(null)).toBe(false)
    expect(isMoneyValue('10 EUR')).toBe(false)
  })
})
