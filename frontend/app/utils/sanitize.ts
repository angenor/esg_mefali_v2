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
