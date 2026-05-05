// F40 T008 — sanitization du SVG Mermaid (R2 / FR-007 / SC-004).
import createDOMPurify from 'dompurify'

type Purify = ReturnType<typeof createDOMPurify>

let cached: Purify | null = null

function getPurify(): Purify | null {
  if (cached) return cached
  if (typeof window === 'undefined') return null
  cached = createDOMPurify(window)
  return cached
}

// Sanitise un SVG Mermaid via le profil DOMPurify SVG. Conserve <title> et <desc>
// (a11y). Retire <script>, on*, javascript:, data: en attributs href/src.
export function sanitizeMermaidSvg(svg: string): string {
  if (typeof svg !== 'string' || svg.length === 0) return ''
  const purify = getPurify()
  if (!purify) return ''
  return purify.sanitize(svg, {
    USE_PROFILES: { svg: true, svgFilters: true },
    ADD_TAGS: ['title', 'desc'],
    ALLOW_DATA_ATTR: false,
  }) as string
}
