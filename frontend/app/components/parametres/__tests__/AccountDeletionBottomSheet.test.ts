// F52 US2 — Test composant AccountDeletionBottomSheet (saisie raison sociale).
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AccountDeletionBottomSheet from '../AccountDeletionBottomSheet.vue'
import { useAccountDeletionStore } from '~/stores/accountDeletion'

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

describe('AccountDeletionBottomSheet', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: 'http://api' } })
    globalThis.useCsrf = () => ({ withCsrf: () => ({}) })
  })

  it('le bouton submit est désactivé tant que confirmation_text est vide', () => {
    const wrapper = mount(AccountDeletionBottomSheet, {
      props: { modelValue: true },
      global: { stubs: { Teleport: true, Transition: true } },
    })
    const submit = wrapper.get('[data-testid="deletion-submit"]')
    expect(submit.attributes('disabled')).toBeDefined()
  })

  it("appelle store.create avec le confirmation_text saisi", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue({
      request: {
        id: 'r1',
        status: 'pending',
        requested_at: '2026-05-05',
        scheduled_for: '2026-06-04',
        can_cancel: true,
      },
    })
    const wrapper = mount(AccountDeletionBottomSheet, {
      props: { modelValue: true },
      global: { stubs: { Teleport: true, Transition: true } },
    })
    await wrapper.get('[data-testid="deletion-confirmation"]').setValue('ACME SARL')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    const store = useAccountDeletionStore()
    expect(store.request?.status).toBe('pending')
  })
})
