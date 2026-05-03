// F40 T009 — mermaidSanitize tests.
import { describe, it, expect } from 'vitest'
import { sanitizeMermaidSvg } from '~/utils/mermaidSanitize'

describe('sanitizeMermaidSvg', () => {
  it('retire les balises <script>', () => {
    const dirty = '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script><g/></svg>'
    const out = sanitizeMermaidSvg(dirty)
    expect(out).not.toContain('<script')
    expect(out).not.toContain('alert')
  })

  it('retire les handlers on* (onclick, onmouseover, …)', () => {
    const dirty = '<svg xmlns="http://www.w3.org/2000/svg"><g onclick="alert(1)" onmouseover="alert(2)"/></svg>'
    const out = sanitizeMermaidSvg(dirty)
    expect(out).not.toMatch(/onclick=/i)
    expect(out).not.toMatch(/onmouseover=/i)
  })

  it('retire les URI javascript: dans href', () => {
    const dirty = '<svg xmlns="http://www.w3.org/2000/svg"><a href="javascript:alert(1)"><text>x</text></a></svg>'
    const out = sanitizeMermaidSvg(dirty)
    expect(out).not.toMatch(/javascript:/i)
  })

  it('conserve <title> et <desc> pour a11y', () => {
    const clean = '<svg xmlns="http://www.w3.org/2000/svg"><title>Diagramme E/S/G</title><desc>Description longue accessible</desc><g/></svg>'
    const out = sanitizeMermaidSvg(clean)
    expect(out).toContain('<title>Diagramme E/S/G</title>')
    expect(out).toContain('<desc>Description longue accessible</desc>')
  })

  it('retourne une chaîne vide pour un input non-string ou vide', () => {
    expect(sanitizeMermaidSvg('')).toBe('')
    // @ts-expect-error null check
    expect(sanitizeMermaidSvg(null)).toBe('')
  })
})
