import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import AskYesNo from '../AskYesNo.vue'

vi.mock('gsap', () => ({
  gsap: {
    fromTo: (_t: unknown, _f: unknown, o: { onComplete?: () => void } = {}) => {
      o.onComplete?.()
      return {}
    },
    to: (_t: unknown, o: { onComplete?: () => void } = {}) => {
      o.onComplete?.()
      return {}
    },
  },
  default: { fromTo: () => {}, to: () => {} },
}))

const fetchMock = vi.fn()
beforeEach(() => {
  setActivePinia(createPinia())
  fetchMock.mockReset()
  ;(globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch
})

const baseInstruction = {
  tool: 'ask_yes_no' as const,
  payload: { question: 'Êtes-vous une SARL ?' },
  context: {
    thread_id: '11111111-1111-1111-1111-111111111111',
    message_id: '22222222-2222-2222-2222-222222222222',
  },
}

describe('AskYesNo', () => {
  it('rend la question et 2 boutons par défaut Oui/Non', async () => {
    const wrapper = mount(AskYesNo, { props: { instruction: baseInstruction }, attachTo: document.body })
    await nextTick()
    expect(wrapper.text()).toContain('Êtes-vous une SARL ?')
    expect(wrapper.find('[data-testid="ask-yes-no-yes"]').text()).toBe('Oui')
    expect(wrapper.find('[data-testid="ask-yes-no-no"]').text()).toBe('Non')
    wrapper.unmount()
  })

  it('respecte les labels personnalisés', async () => {
    const wrapper = mount(AskYesNo, {
      props: {
        instruction: { ...baseInstruction, payload: { question: 'Q ?', yes_label: 'Bien sûr', no_label: 'Pas du tout' } },
      },
      attachTo: document.body,
    })
    await nextTick()
    expect(wrapper.find('[data-testid="ask-yes-no-yes"]').text()).toBe('Bien sûr')
    expect(wrapper.find('[data-testid="ask-yes-no-no"]').text()).toBe('Pas du tout')
    wrapper.unmount()
  })

  it('soumet le bon payload sur clic Oui (status 200)', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ id: 'msg-1', thread_id: 't', role: 'pme', content: 'Oui', created_at: 'now' }), {
        status: 200,
      }),
    )
    const wrapper = mount(AskYesNo, { props: { instruction: baseInstruction }, attachTo: document.body })
    await nextTick()
    await wrapper.find('[data-testid="ask-yes-no-yes"]').trigger('click')
    await nextTick()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const body = JSON.parse((fetchMock.mock.calls[0]![1] as RequestInit).body as string)
    expect(body.payload_json).toEqual({ tool: 'ask_yes_no', value: true, label: 'Oui' })
    wrapper.unmount()
  })

  it('échec 5xx → émet error retriable', async () => {
    fetchMock.mockResolvedValue(new Response('boom', { status: 503 }))
    const wrapper = mount(AskYesNo, { props: { instruction: baseInstruction }, attachTo: document.body })
    await nextTick()
    await wrapper.find('[data-testid="ask-yes-no-yes"]').trigger('click')
    await nextTick()
    const errors = wrapper.emitted('error')
    expect(errors).toBeTruthy()
    expect((errors![0]![0] as { retriable: boolean }).retriable).toBe(true)
    wrapper.unmount()
  })
})
