// F40 T017 — VizSourcePin tests.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import VizSourcePin from '~/components/viz/VizSourcePin.vue'
import { __setSourcesFetcher } from '~/stores/sources'

const VALID = {
  source_id: 'src_abc',
  title: 'Rapport GIEC',
  url: 'https://example.org/giec',
  pillar: 'E',
  valid_from: '2024-01-01',
  status: 'verified',
}

function ok(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'content-type': 'application/json' },
  })
}

describe('VizSourcePin', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })
  afterEach(() => {
    __setSourcesFetcher(null)
  })

  it('rend un bouton accessible avec aria-haspopup', () => {
    __setSourcesFetcher(async () => ok(VALID))
    const w = mount(VizSourcePin, { props: { source_id: 'src_abc' } })
    const btn = w.get('button')
    expect(btn.attributes('aria-haspopup')).toBe('dialog')
    expect(btn.attributes('aria-expanded')).toBe('false')
  })

  it('ouvre la popover au clic et affiche titre/url/pillar', async () => {
    __setSourcesFetcher(async () => ok(VALID))
    const w = mount(VizSourcePin, { props: { source_id: 'src_abc' } })
    await w.get('button').trigger('click')
    await flushPromises()
    const html = w.html()
    expect(html).toContain('Rapport GIEC')
    expect(html).toContain('https://example.org/giec')
    expect(html).toMatch(/E<\/span>/)
    expect(w.get('button').attributes('aria-expanded')).toBe('true')
  })

  it('cas revoked : affiche message d\'alerte', async () => {
    __setSourcesFetcher(async () => ok({ ...VALID, status: 'revoked', revoked_reason: 'expirée' }))
    const w = mount(VizSourcePin, { props: { source_id: 'src_abc' } })
    await w.get('button').trigger('click')
    await flushPromises()
    expect(w.html()).toMatch(/révoquée/)
    expect(w.html()).toContain('expirée')
  })

  it('404 : composant invisible (fail-silent)', async () => {
    __setSourcesFetcher(async () => new Response('{}', { status: 404 }))
    const w = mount(VizSourcePin, { props: { source_id: 'missing' } })
    await w.get('button').trigger('click')
    await flushPromises()
    expect(w.find('button').exists()).toBe(false)
  })

  it('lien externe utilise rel="noopener noreferrer"', async () => {
    __setSourcesFetcher(async () => ok(VALID))
    const w = mount(VizSourcePin, { props: { source_id: 'src_abc' } })
    await w.get('button').trigger('click')
    await flushPromises()
    const a = w.get('a')
    expect(a.attributes('rel')).toContain('noopener')
    expect(a.attributes('target')).toBe('_blank')
  })

  it('pillar inconnu : log console.error et fallback neutre', async () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    __setSourcesFetcher(async () => ok({ ...VALID, pillar: 'unknown_x' }))
    const w = mount(VizSourcePin, { props: { source_id: 'src_abc' } })
    await w.get('button').trigger('click')
    await flushPromises()
    expect(spy).toHaveBeenCalled()
    spy.mockRestore()
    expect(w.html()).toContain('methodology')
  })
})
