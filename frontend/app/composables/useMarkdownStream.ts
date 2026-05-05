/**
 * useMarkdownStream — rendu Markdown tolérant aux fragments + sanitisation stricte.
 *
 * Référence : specs/041-chat-conversational-layer/research.md R2 + R10.
 * markdown-it est tolérant aux Markdown malformés (`**bold` non clos rend
 * littéralement puis se reformate quand `**` arrive). La sortie HTML passe par
 * DOMPurify avec une allow-list serrée avant injection via v-html.
 */
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const ALLOWED_TAGS = [
  'p', 'br', 'hr',
  'strong', 'em', 's', 'del',
  'code', 'pre',
  'ul', 'ol', 'li',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'table', 'thead', 'tbody', 'tr', 'th', 'td',
  'a',
  'blockquote',
  'sup', 'sub',
  'span',
]

const ALLOWED_ATTR = ['href', 'rel', 'target', 'class', 'title']

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: false,
})
md.enable(['table'])

DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('rel', 'noopener noreferrer')
    node.setAttribute('target', '_blank')
  }
})

const PURIFY_CONFIG = {
  ALLOWED_TAGS,
  ALLOWED_ATTR,
  FORBID_ATTR: ['style'],
  ALLOW_DATA_ATTR: false,
  ALLOWED_URI_REGEXP: /^(?:(?:https):|mailto:|#|\/)/i,
} as const

export interface UseMarkdownStream {
  render: (content: string) => string
}

export function useMarkdownStream(): UseMarkdownStream {
  return {
    render(content: string): string {
      if (!content) return ''
      const rawHtml = md.render(content)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const clean = DOMPurify.sanitize(rawHtml, PURIFY_CONFIG as any)
      return typeof clean === 'string' ? clean : String(clean)
    },
  }
}
