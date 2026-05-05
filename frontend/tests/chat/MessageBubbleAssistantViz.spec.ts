/**
 * F41 / US5 (T041). MessageBubbleAssistant : routage des viz F40 selon
 * payload.tool ; payload.kind === 'error' rend MessageError.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MessageBubbleAssistant from '~/components/chat/MessageBubbleAssistant.vue'

describe('MessageBubbleAssistant — viz routing', () => {
  it("rend du Markdown quand payload est null", () => {
    const wrapper = mount(MessageBubbleAssistant, {
      props: { messageId: 'a1', content: 'Salut **mondé**', payload: null },
    })
    expect(wrapper.find('.chat-md').exists()).toBe(true)
    expect(wrapper.html()).toContain('mondé')
  })

  it("rend MessageError pour payload.kind === 'error'", () => {
    const wrapper = mount(MessageBubbleAssistant, {
      props: {
        messageId: 'a1',
        content: '',
        payload: { kind: 'error', code: 'timeout', message: 'plouf', retryOf: 'a1' },
      },
    })
    expect(wrapper.find('.chat-error').exists()).toBe(true)
    expect(wrapper.text()).toContain('plouf')
  })

  it("propage l'event retry depuis MessageError", async () => {
    const wrapper = mount(MessageBubbleAssistant, {
      props: {
        messageId: 'a1',
        content: '',
        payload: { kind: 'error', code: 'timeout', message: 'oops', retryOf: 'a1' },
      },
    })
    await wrapper.find('.chat-error__retry').trigger('click')
    expect(wrapper.emitted('retry')).toBeTruthy()
    expect(wrapper.emitted('retry')![0]).toEqual(['a1'])
  })

  it("rend l'indicateur mutation quand hasMutation est true", () => {
    const wrapper = mount(MessageBubbleAssistant, {
      props: { messageId: 'a1', content: 'OK', payload: null, hasMutation: true },
    })
    expect(wrapper.find('.chat-bubble-assistant__mutation').exists()).toBe(true)
  })

  it("ajoute la classe 'wide' pour les payloads viz", () => {
    const wrapper = mount(MessageBubbleAssistant, {
      props: {
        messageId: 'a1',
        content: '',
        payload: { kind: 'viz', tool: 'kpi', data: { value: 42, unit: 'kg' } },
      },
      global: { stubs: { ClientOnly: true } },
    })
    expect(wrapper.find('.chat-bubble-assistant--wide').exists()).toBe(true)
  })
})
