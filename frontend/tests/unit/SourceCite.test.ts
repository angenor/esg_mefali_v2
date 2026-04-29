/**
 * F03 US4 — Tests Vitest <SourceCite>.
 */
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import SourceCite from '../../app/components/source/SourceCite.vue'

describe('<SourceCite>', () => {
  it('renders the picto button', () => {
    const w = mount(SourceCite, {
      props: { sourceIds: ['11111111-1111-1111-1111-111111111111'] },
    })
    const btn = w.find('button.picto')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('aria-label')).toBe('Voir les sources de cette donnée')
  })

  it('opens the bottom sheet on click and emits open event', async () => {
    // Stub fetch to avoid network call
    const original = globalThis.fetch
    globalThis.fetch = vi.fn(async () => new Response('{}', { status: 404 })) as never
    const w = mount(SourceCite, {
      props: { sourceIds: ['00000000-0000-0000-0000-000000000001'] },
    })
    await w.find('button.picto').trigger('click')
    expect(w.emitted().open).toBeTruthy()
    expect(w.emitted().open?.[0]?.[0]).toEqual({
      sourceIds: ['00000000-0000-0000-0000-000000000001'],
    })
    globalThis.fetch = original
  })

  it('respects size prop', () => {
    const w = mount(SourceCite, {
      props: { sourceIds: ['x'], size: 'lg' },
    })
    expect(w.classes()).toContain('cite-lg')
  })
})
