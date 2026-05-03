/**
 * F41 / US9 (T056). MemoryBadge : taille + ouverture modale.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import MemoryBadge from '~/components/chat/MemoryBadge.vue'
import { useChatStore } from '~/stores/chat'

describe('MemoryBadge', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        threadId: 't1',
        size: 5,
        entries: [{ kind: 'fact', preview: 'CA 2025 = 12 M' }],
        fetchedAt: '2026-05-03T12:00:00Z',
      }), { status: 200 }),
    ) as never
  })

  it("affiche la taille quand snapshot disponible", async () => {
    const store = useChatStore()
    store.memorySnapshots = {
      t1: { threadId: 't1', size: 7, entries: [], fetchedAt: '' },
    }
    const wrapper = mount(MemoryBadge, { props: { threadId: 't1' } })
    expect(wrapper.find('.memory-badge__count').text()).toBe('7')
  })

  it("ouvre la modale au click et liste les entrées", async () => {
    const store = useChatStore()
    store.memorySnapshots = {
      t1: {
        threadId: 't1',
        size: 1,
        entries: [{ kind: 'fact', preview: 'CA 2025 = 12 M' }],
        fetchedAt: '',
      },
    }
    const wrapper = mount(MemoryBadge, { props: { threadId: 't1' } })
    await wrapper.find('.memory-badge__btn').trigger('click')
    expect(wrapper.find('.memory-badge__modal').exists()).toBe(true)
    expect(wrapper.text()).toContain('CA 2025 = 12 M')
  })

  it("appelle fetchMemorySnapshot au mount", async () => {
    mount(MemoryBadge, { props: { threadId: 't1' } })
    await flushPromises()
    expect(globalThis.fetch).toHaveBeenCalled()
  })
})
