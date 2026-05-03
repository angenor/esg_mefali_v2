/**
 * F41 / US1 (T023). MessageMarkdown : sanitisation XSS + tolérance fragments.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MessageMarkdown from '~/components/chat/MessageMarkdown.vue'

describe('MessageMarkdown — sanitisation', () => {
  it('strippe <script>', () => {
    const wrapper = mount(MessageMarkdown, {
      props: { content: 'Bonjour <script>alert(1)</script> texte' },
    })
    // Le HTML brut est échappé par markdown-it (html: false) et reste inerte.
    expect(wrapper.element.querySelector('script')).toBeNull()
    expect(wrapper.html()).not.toMatch(/<script[^>]*>/i)
  })

  it("ne rend pas de tag <img> brut depuis du HTML inline", () => {
    const wrapper = mount(MessageMarkdown, {
      props: { content: '<img src=x onerror=alert(1)>' },
    })
    // markdown-it html:false → balise HTML inline est échappée et inerte
    expect(wrapper.find('img').exists()).toBe(false)
    // le contenu "onerror=" peut apparaître échappé en texte mais n'est pas exécutable
    const imgEl = wrapper.element.querySelector('img')
    expect(imgEl).toBeNull()
  })

  it('strippe les liens javascript:', () => {
    const wrapper = mount(MessageMarkdown, {
      props: { content: '[clic](javascript:alert(1))' },
    })
    const html = wrapper.html()
    expect(html).not.toMatch(/href=["']?javascript:/i)
  })

  it('rend les liens https avec rel/target sécurisés', () => {
    const wrapper = mount(MessageMarkdown, {
      props: { content: '[ok](https://example.org)' },
    })
    const html = wrapper.html()
    expect(html).toContain('rel="noopener noreferrer"')
    expect(html).toContain('target="_blank"')
  })

  it("ne crashe pas sur un Markdown partiel non-clos", () => {
    expect(() =>
      mount(MessageMarkdown, { props: { content: '**bold sans fermeture' } }),
    ).not.toThrow()
  })

  it('rend le curseur clignotant en streaming', () => {
    const wrapper = mount(MessageMarkdown, {
      props: { content: 'partiel', streaming: true },
    })
    expect(wrapper.find('.chat-md__cursor').exists()).toBe(true)
  })

  it('rend les tables GFM', () => {
    const md = '| a | b |\n|---|---|\n| 1 | 2 |'
    const wrapper = mount(MessageMarkdown, { props: { content: md } })
    expect(wrapper.html()).toContain('<table>')
    expect(wrapper.html()).toContain('<td>1</td>')
  })
})
