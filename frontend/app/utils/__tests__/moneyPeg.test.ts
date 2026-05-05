import { describe, expect, it } from 'vitest'
import { eurToXof, xofToEur, XOF_PER_EUR } from '../moneyPeg'

describe('moneyPeg (peg fixe XOF↔EUR)', () => {
  it('expose la constante 655.957', () => {
    expect(XOF_PER_EUR).toBe('655.957')
  })

  it('eurToXof(1) = 656 (arrondi)', () => {
    expect(eurToXof('1', { decimals: 0 })).toBe('655')
  })

  it('eurToXof(1000.50) ≈ 656284 (1000.5 × 655.957 = 656284.1085, troncature)', () => {
    expect(eurToXof('1000.50', { decimals: 0 })).toBe('656284')
  })

  it('xofToEur(655957) = 1000.00 EUR', () => {
    expect(xofToEur('655957', { decimals: 2 })).toBe('1000.00')
  })

  it('xofToEur(1000) ≈ 1.52 EUR', () => {
    const v = xofToEur('1000', { decimals: 2 })
    expect(v).toBe('1.52')
  })

  it('rejette une string non décimale', () => {
    expect(() => eurToXof('abc')).toThrow()
  })
})
