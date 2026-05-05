import { describe, it, expect } from 'vitest'
import { classifyCreditScore } from '~/lib/classifyCreditScore'

describe('classifyCreditScore — bornes (clarif Q2, bornes inférieures inclusives)', () => {
  it.each([
    [0, 'insuffisant'],
    [39, 'insuffisant'],
    [40, 'a_ameliorer'],
    [59, 'a_ameliorer'],
    [60, 'bon'],
    [79, 'bon'],
    [80, 'excellent'],
    [100, 'excellent'],
  ])('score %d → bucket %s', (score, expected) => {
    expect(classifyCreditScore(score).bucket).toBe(expected)
  })

  it('hors borne basse → clamp insuffisant', () => {
    expect(classifyCreditScore(-10).bucket).toBe('insuffisant')
  })
  it('hors borne haute → clamp excellent', () => {
    expect(classifyCreditScore(150).bucket).toBe('excellent')
  })
  it('label et colorToken alignés', () => {
    const c = classifyCreditScore(72)
    expect(c.label).toBe('Bon')
    expect(c.colorToken).toBe('success')
  })
})
