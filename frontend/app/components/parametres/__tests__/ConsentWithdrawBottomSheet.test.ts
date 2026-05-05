// F52 US2 — Test ConsentWithdrawBottomSheet.
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ConsentWithdrawBottomSheet from '../ConsentWithdrawBottomSheet.vue'

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

describe('ConsentWithdrawBottomSheet', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: 'http://api' } })
    globalThis.useCsrf = () => ({ withCsrf: () => ({}) })
  })

  it("appelle POST /withdraw puis émet close", async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce(undefined) // POST withdraw
      .mockResolvedValueOnce([]) // load après withdraw
    globalThis.$fetch = fetch
    const wrapper = mount(ConsentWithdrawBottomSheet, {
      props: { consentId: 'c1' },
      global: { stubs: { Teleport: true, Transition: true } },
    })
    await wrapper.get('[data-testid="consent-withdraw-confirm"]').trigger('click')
    await flushPromises()
    expect(fetch).toHaveBeenCalled()
    const url = fetch.mock.calls[0][0] as string
    expect(url).toMatch(/\/me\/consents\/c1\/withdraw$/)
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
