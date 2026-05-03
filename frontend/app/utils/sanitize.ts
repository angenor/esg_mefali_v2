import createDOMPurify from 'dompurify'

export interface SanitizeOptions {
  allowedTags?: string[]
  allowedAttr?: string[]
}

const DEFAULT_TAGS = ['a', 'b', 'strong', 'i', 'em', 'br', 'p', 'ul', 'ol', 'li', 'span']
const DEFAULT_ATTR = ['href', 'title', 'target', 'rel']

type Purify = ReturnType<typeof createDOMPurify>

let cached: Purify | null = null

function getPurify(): Purify | null {
  if (cached) return cached
  if (typeof window === 'undefined') return null
  // En navigateur ET en happy-dom, l'appel par défaut binde le window courant.
  // On le réinstancie explicitement pour éviter une race en SSR-then-client.
  cached = createDOMPurify(window)
  return cached
}

// Wrapper unique DOMPurify (R-005). Tout `v-html` doit passer par cette fonction.
export function sanitizeHtml(html: string, options: SanitizeOptions = {}): string {
  if (typeof html !== 'string' || html.length === 0) {
    return ''
  }
  const purify = getPurify()
  if (!purify) {
    // SSR : on renvoie une chaîne vide plutôt que de pousser du HTML non-sanitizé.
    return ''
  }
  return purify.sanitize(html, {
    ALLOWED_TAGS: options.allowedTags ?? DEFAULT_TAGS,
    ALLOWED_ATTR: options.allowedAttr ?? DEFAULT_ATTR,
    ALLOW_DATA_ATTR: false,
  }) as string
}

// Sortie purement textuelle : tout HTML est strippé (utilisé pour `label`,
// `description`, `source_label` reçus du backend dans les payloads tools — F39 R4).
export function sanitizeText(input: unknown): string {
  if (typeof input !== 'string' || input.length === 0) return ''
  const purify = getPurify()
  if (!purify) {
    return input.replace(/<[^>]*>/g, '')
  }
  return purify.sanitize(input, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] }) as string
}

// Alias courts attendus par les wrappers F39 (cf. tasks T005).
export const text = sanitizeText
export const safeHtml = sanitizeHtml
