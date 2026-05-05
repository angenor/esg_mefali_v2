// F40 T034 — VizMermaidRenderer tests : sanitization + fallback.
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

const STUBS = { ClientOnly: { template: '<div><slot/></div>' } }

vi.mock('mermaid', () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn(async (id: string, script: string) => {
      if (script.includes('INVALID')) throw new Error('parse error')
      return {
        svg: `<svg xmlns="http://www.w3.org/2000/svg" id="${id}"><script>alert(1)</script><g><text>${script}</text></g></svg>`,
      }
    }),
  },
}))

import VizMermaidRenderer from '~/components/viz/VizMermaidRenderer.vue'

describe('VizMermaidRenderer', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('script valide → SVG sanitisé sans <script>', async () => {
    const w = mount(VizMermaidRenderer, {
      props: { payload: { script: 'graph TD; A-->B' } },
      global: { stubs: STUBS },
    })
    await flushPromises()
    const html = w.html()
    expect(html).toContain('<svg')
    expect(html).not.toContain('<script')
    expect(html).not.toContain('alert(1)')
  })

  it('script invalide → fallback <pre> avec source brut sans crash', async () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const w = mount(VizMermaidRenderer, {
      props: { payload: { script: 'INVALID syntax' } },
      global: { stubs: STUBS },
    })
    await flushPromises()
    expect(w.find('.viz-mermaid__fallback').exists()).toBe(true)
    expect(w.text()).toContain('INVALID syntax')
    expect(spy).toHaveBeenCalled()
    spy.mockRestore()
  })

  it('aria-label fourni est inséré comme <title> dans le SVG', async () => {
    const w = mount(VizMermaidRenderer, {
      props: {
        payload: { script: 'graph TD; A-->B' },
        ariaLabel: 'Diagramme E/S/G',
      },
      global: { stubs: STUBS },
    })
    await flushPromises()
    expect(w.html()).toContain('<title>Diagramme E/S/G</title>')
  })
})
