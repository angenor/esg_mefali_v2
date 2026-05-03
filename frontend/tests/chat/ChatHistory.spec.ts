/**
 * F41 / US1 (T025). ChatHistory : scroll-pinning conditionnel.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatHistory from '~/components/chat/ChatHistory.vue'
import type { ChatMessage } from '~/types/chat'

function msg(overrides: Partial<ChatMessage>): ChatMessage {
  return {
    id: overrides.id ?? 'm',
    threadId: 't1',
    role: overrides.role ?? 'user',
    content: overrides.content ?? '',
    payload: overrides.payload ?? null,
    createdAt: '2026-05-03T10:00:00Z',
    ...overrides,
  }
}

describe('ChatHistory', () => {
  it('rend les bulles user/assistant', () => {
    const wrapper = mount(ChatHistory, {
      props: {
        messages: [
          msg({ id: 'u1', role: 'user', content: 'Bonjour' }),
          msg({ id: 'a1', role: 'assistant', content: 'Salut' }),
        ],
      },
    })
    const html = wrapper.html()
    expect(html).toContain('Bonjour')
    expect(html).toContain('Salut')
  })

  it("affiche le typing indicator quand showTyping est true", () => {
    const wrapper = mount(ChatHistory, {
      props: { messages: [], showTyping: true },
    })
    expect(wrapper.find('.chat-typing').exists()).toBe(true)
  })

  it("ne rend pas le typing si showTyping est false", () => {
    const wrapper = mount(ChatHistory, {
      props: { messages: [msg({ id: 'a1', role: 'assistant', content: 'ok' })], showTyping: false },
    })
    expect(wrapper.find('.chat-typing').exists()).toBe(false)
  })

  it("propage l'event retry", async () => {
    const wrapper = mount(ChatHistory, {
      props: {
        messages: [msg({
          id: 'a1',
          role: 'assistant',
          content: '',
          payload: { kind: 'error', code: 'timeout', message: 'oops', retryOf: 'a1' },
        })],
      },
    })
    const btn = wrapper.find('.chat-error__retry')
    expect(btn.exists()).toBe(true)
    await btn.trigger('click')
    expect(wrapper.emitted('retry')).toBeTruthy()
    expect(wrapper.emitted('retry')![0]).toEqual(['a1'])
  })
})
