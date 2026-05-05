/**
 * F41 / Polish (T059). Suite XSS — 10 payloads OWASP, aucune exécution possible.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MessageMarkdown from '~/components/chat/MessageMarkdown.vue'

const XSS_PAYLOADS: Array<{ name: string; payload: string; mustNotContain: RegExp }> = [
  { name: 'script tag', payload: '<script>alert(1)</script>', mustNotContain: /<script[^>]*>/i },
  { name: 'img onerror', payload: '<img src=x onerror=alert(1)>', mustNotContain: /<img[^>]*onerror/i },
  { name: 'javascript: link', payload: '[x](javascript:alert(1))', mustNotContain: /href=["']?javascript:/i },
  { name: 'iframe', payload: '<iframe src="https://evil"></iframe>', mustNotContain: /<iframe/i },
  { name: 'object', payload: '<object data="evil"></object>', mustNotContain: /<object/i },
  { name: 'embed', payload: '<embed src="evil">', mustNotContain: /<embed/i },
  { name: 'svg onload', payload: '<svg onload=alert(1)>', mustNotContain: /<svg[^>]*onload/i },
  { name: 'data: uri', payload: '[x](data:text/html,<script>alert(1)</script>)', mustNotContain: /href=["']?data:/i },
  { name: 'meta refresh', payload: '<meta http-equiv="refresh" content="0;url=evil">', mustNotContain: /<meta/i },
  { name: 'style with expression', payload: '<div style="background:url(javascript:alert(1))">x</div>', mustNotContain: /<div[^>]*style=/i },
]

describe('MessageMarkdown — XSS suite (OWASP)', () => {
  for (const { name, payload, mustNotContain } of XSS_PAYLOADS) {
    it(`neutralise ${name}`, () => {
      const wrapper = mount(MessageMarkdown, { props: { content: payload } })
      const html = wrapper.html()
      expect(html).not.toMatch(mustNotContain)
    })
  }
})
