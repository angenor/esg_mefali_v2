/**
 * F41 / US4 (T038). ThreadList : tri DESC, virtualisation au-delà de 50, events.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ThreadList from '~/components/chat/ThreadList.vue'
import type { ChatThreadSummary } from '~/types/chat'

function makeThread(id: string, hoursAgo: number): ChatThreadSummary {
  const d = new Date(Date.now() - hoursAgo * 3600_000)
  return {
    id,
    title: `Thread ${id}`,
    lastMessageAt: d.toISOString(),
    createdAt: d.toISOString(),
    archived: false,
  }
}

describe('ThreadList', () => {
  it('trie DESC par lastMessageAt', () => {
    const threads = [
      makeThread('a', 24),
      makeThread('b', 1),
      makeThread('c', 12),
    ]
    const wrapper = mount(ThreadList, { props: { threads } })
    const titles = wrapper.findAll('.thread-list__title').map((n) => n.text())
    expect(titles).toEqual(['Thread b', 'Thread c', 'Thread a'])
  })

  it('masque les threads archivés', () => {
    const threads = [
      makeThread('a', 1),
      { ...makeThread('b', 2), archived: true },
    ]
    const wrapper = mount(ThreadList, { props: { threads } })
    expect(wrapper.findAll('.thread-list__item')).toHaveLength(1)
  })

  it("émet `select` au click sur un thread", async () => {
    const threads = [makeThread('a', 1)]
    const wrapper = mount(ThreadList, { props: { threads } })
    await wrapper.find('.thread-list__item').trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('select')![0]).toEqual(['a'])
  })

  it("émet `new-chat` au click sur le bouton Nouveau chat", async () => {
    const wrapper = mount(ThreadList, { props: { threads: [] } })
    await wrapper.find('.thread-list__new').trigger('click')
    expect(wrapper.emitted('new-chat')).toBeTruthy()
  })

  it("met une classe active sur le thread courant", () => {
    const threads = [makeThread('a', 1), makeThread('b', 2)]
    const wrapper = mount(ThreadList, { props: { threads, currentId: 'b' } })
    const active = wrapper.find('.thread-list__item--active')
    expect(active.exists()).toBe(true)
    expect(active.text()).toContain('Thread b')
  })
})
