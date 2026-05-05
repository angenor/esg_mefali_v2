import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import ChatBottomSheet from '../ChatBottomSheet.vue'
import { useChatBottomSheetStore } from '~/stores/chatBottomSheet'

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

beforeEach(() => {
  setActivePinia(createPinia())
})

const validInst = {
  tool: 'ask_yes_no' as const,
  payload: { question: 'Q ?' },
  context: { thread_id: '11111111-1111-1111-1111-111111111111', message_id: '22222222-2222-2222-2222-222222222222' },
}

describe('ChatBottomSheet (orchestrateur)', () => {
  it('reste vide tant que store.current === null', async () => {
    const wrapper = mount(ChatBottomSheet, { attachTo: document.body })
    await nextTick()
    expect(document.querySelector('[data-testid="chat-bottom-sheet"]')).toBeNull()
    wrapper.unmount()
  })

  it('refuse un payload invalide (un sheet ne s\'ouvre pas)', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const wrapper = mount(ChatBottomSheet, { attachTo: document.body })
    await nextTick()
    // open est exposé via defineExpose
    await (wrapper.vm as unknown as { open: (i: unknown) => Promise<void> }).open({ tool: 'ask_yes_no', payload: {}, context: {} })
    await nextTick()
    const store = useChatBottomSheetStore()
    expect(store.current).toBeNull()
    expect(warn).toHaveBeenCalled()
    warn.mockRestore()
    wrapper.unmount()
  })

  it('open(instruction valide) place store.current', async () => {
    const wrapper = mount(ChatBottomSheet, { attachTo: document.body })
    await nextTick()
    await (wrapper.vm as unknown as { open: (i: unknown) => Promise<void> }).open(validInst)
    await nextTick()
    const store = useChatBottomSheetStore()
    expect(store.current).not.toBeNull()
    expect(store.current?.tool).toBe('ask_yes_no')
    wrapper.unmount()
  })

  it('un second open est ignoré tant qu\'un sheet est déjà ouvert', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const wrapper = mount(ChatBottomSheet, { attachTo: document.body })
    await nextTick()
    const expose = wrapper.vm as unknown as { open: (i: unknown) => Promise<void> }
    await expose.open(validInst)
    await expose.open({ ...validInst, payload: { question: 'Autre ?' } })
    await nextTick()
    const store = useChatBottomSheetStore()
    expect(store.current?.payload.question).toBe('Q ?')
    expect(warn).toHaveBeenCalled()
    warn.mockRestore()
    wrapper.unmount()
  })
})
