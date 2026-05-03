// F38 T053 — Tests TheOfflineBanner
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

const isOnline = ref(true)
vi.mock('~/composables/useOnlineStatus', () => ({
  useOnlineStatus: () => ({ isOnline }),
}))

import TheOfflineBanner from '../../../app/components/shell/TheOfflineBanner.vue'

describe('TheOfflineBanner', () => {
  it('masqué si online', () => {
    isOnline.value = true
    const w = mount(TheOfflineBanner)
    expect(w.find('[data-testid="offline-banner"]').exists()).toBe(false)
  })

  it('visible et a11y si offline', () => {
    isOnline.value = false
    const w = mount(TheOfflineBanner)
    const el = w.find('[data-testid="offline-banner"]')
    expect(el.exists()).toBe(true)
    expect(el.attributes('role')).toBe('status')
    expect(el.attributes('aria-live')).toBe('polite')
  })
})
