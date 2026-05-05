import { describe, it, expect } from 'vitest'
import { useMoneyFormat } from '../../../app/composables/useMoneyFormat'

describe('useMoneyFormat', () => {
  it('formats XOF with precision 0', () => {
    const f = useMoneyFormat({ currency: 'XOF' })
    const out = f.display(1234567)
    expect(out).toMatch(/1[\s  ]?234[\s  ]?567/)
    expect(out).not.toMatch(/[,.]\d/)
  })

  it('formats EUR with precision 2', () => {
    const f = useMoneyFormat({ currency: 'EUR' })
    const out = f.display(1234.5)
    expect(out).toMatch(/1[\s  ]?234,50/)
  })

  it('formats USD with precision 2', () => {
    const f = useMoneyFormat({ currency: 'USD' })
    expect(f.display(99.9)).toMatch(/99,90/)
  })

  it('parses fr-FR formatted numbers', () => {
    const f = useMoneyFormat({ currency: 'EUR' })
    expect(f.parse('1 234,50')).toBeCloseTo(1234.5, 2)
    expect(f.parse('1 234,5 €')).toBeCloseTo(1234.5, 2)
  })

  it('returns null for invalid or empty input', () => {
    const f = useMoneyFormat({ currency: 'EUR' })
    expect(f.parse('')).toBeNull()
    expect(f.parse('abc')).toBeNull()
  })

  it('display returns empty string for null/undefined', () => {
    const f = useMoneyFormat({ currency: 'EUR' })
    expect(f.display(null)).toBe('')
    expect(f.display(undefined)).toBe('')
  })
})
