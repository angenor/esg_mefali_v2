// F52 US2 — Test EmailChangeBottomSheet (validation simple + appel POST).
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import EmailChangeBottomSheet from '../EmailChangeBottomSheet.vue'

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

describe('EmailChangeBottomSheet', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: 'http://api' } })
    globalThis.useCsrf = () => ({ withCsrf: () => ({}) })
  })

  it("submit désactivé tant que les champs sont vides", () => {
    const wrapper = mount(EmailChangeBottomSheet, {
      props: { modelValue: true, currentEmail: 'a@b.fr' },
      global: { stubs: { Teleport: true, Transition: true } },
    })
    const submit = wrapper.get('[data-testid="email-change-submit"]')
    expect(submit.attributes('disabled')).toBeDefined()
  })

  it("appelle POST /me/email-change avec new_email et password", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      email_pending: 'new@example.com',
      verification_sent_at: '2026-05-05T00:00:00Z',
    })
    globalThis.$fetch = fetchMock
    const wrapper = mount(EmailChangeBottomSheet, {
      props: { modelValue: true, currentEmail: 'old@example.com' },
      global: { stubs: { Teleport: true, Transition: true } },
    })
    await wrapper.get('[data-testid="email-change-new"]').setValue('new@example.com')
    await wrapper.get('[data-testid="email-change-password"]').setValue('Pass1234')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(fetchMock).toHaveBeenCalled()
    const call = fetchMock.mock.calls[0]
    expect(call[0]).toMatch(/\/me\/email-change$/)
    expect(call[1]?.body?.new_email).toBe('new@example.com')
  })
})
