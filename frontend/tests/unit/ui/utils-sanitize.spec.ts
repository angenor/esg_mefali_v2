import { describe, it, expect, vi } from 'vitest'

// happy-dom n'expose pas tout ce qu'attend DOMPurify ; on mocke pour valider
// que notre wrapper applique bien la whitelist par défaut et délègue.
const sanitizeSpy = vi.fn((html: string) => {
  // Reproduit le comportement attendu : strip script, strip javascript:.
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/javascript:/gi, '')
})

vi.mock('dompurify', () => {
  return {
    default: () => ({
      sanitize: sanitizeSpy,
      isSupported: true,
    }),
  }
})

import { sanitizeHtml } from '../../../app/utils/sanitize'

describe('sanitizeHtml', () => {
  it('strips <script> tags via DOMPurify', () => {
    const out = sanitizeHtml('<p>ok</p><script>alert(1)</script>')
    expect(out).not.toContain('<script')
    expect(out).toContain('ok')
    expect(sanitizeSpy).toHaveBeenCalled()
  })

  it('passes default allowedTags (a kept) to DOMPurify', () => {
    sanitizeHtml('<a href="https://example.com">x</a>')
    const lastCall = sanitizeSpy.mock.calls.at(-1)!
    const config = lastCall[1] as { ALLOWED_TAGS?: string[]; ALLOWED_ATTR?: string[] }
    expect(config.ALLOWED_TAGS).toContain('a')
    expect(config.ALLOWED_ATTR).toContain('href')
  })

  it('strips javascript: URLs', () => {
    const out = sanitizeHtml('<a href="javascript:alert(1)">x</a>')
    expect(out).not.toContain('javascript:')
  })

  it('returns empty string for non-string or empty input', () => {
    expect(sanitizeHtml('')).toBe('')
    // @ts-expect-error invalid input
    expect(sanitizeHtml(null)).toBe('')
  })

  it('forwards custom allowedTags / allowedAttr', () => {
    sanitizeHtml('<b>x</b>', { allowedTags: ['b'], allowedAttr: ['data-x'] })
    const lastCall = sanitizeSpy.mock.calls.at(-1)!
    const config = lastCall[1] as { ALLOWED_TAGS?: string[]; ALLOWED_ATTR?: string[] }
    expect(config.ALLOWED_TAGS).toEqual(['b'])
    expect(config.ALLOWED_ATTR).toEqual(['data-x'])
  })
})
