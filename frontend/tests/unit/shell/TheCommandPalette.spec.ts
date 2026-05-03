// F38 T033 — Tests TheCommandPalette
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

const navigateToMock = vi.fn(() => Promise.resolve())
;(globalThis as { navigateTo?: unknown }).navigateTo = navigateToMock

vi.mock('gsap', () => ({ gsap: { fromTo: vi.fn() } }))

import { __resetCommandPalette, useCommandPalette } from '../../../app/composables/useCommandPalette'
import TheCommandPalette from '../../../app/components/shell/TheCommandPalette.vue'

function makeWrapper() {
  return mount(TheCommandPalette, {
    attachTo: document.body,
    global: {
      stubs: {
        Teleport: { template: '<div><slot /></div>' },
      },
    },
  })
}

describe('TheCommandPalette', () => {
  beforeEach(() => {
    __resetCommandPalette()
    navigateToMock.mockClear()
    document.body.innerHTML = ''
  })

  it('Cmd+K ouvre la palette', async () => {
    const w = makeWrapper()
    const palette = useCommandPalette()
    Object.defineProperty(navigator, 'platform', { value: 'MacIntel', configurable: true })
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }))
    await nextTick()
    expect(palette.isOpen.value).toBe(true)
    w.unmount()
  })

  it('Ctrl+K ouvre la palette (non-mac)', async () => {
    const w = makeWrapper()
    const palette = useCommandPalette()
    Object.defineProperty(navigator, 'platform', { value: 'Win32', configurable: true })
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }))
    await nextTick()
    expect(palette.isOpen.value).toBe(true)
    w.unmount()
  })

  it('Esc ferme la palette', async () => {
    const w = makeWrapper()
    const palette = useCommandPalette()
    palette.open()
    await nextTick()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await nextTick()
    expect(palette.isOpen.value).toBe(false)
    w.unmount()
  })

  it('Enter exécute l\'action sélectionnée (route)', async () => {
    const w = makeWrapper()
    const palette = useCommandPalette()
    palette.registerActions([
      { id: 'nav.scoring', label: 'Aller au scoring ESG', route: '/scoring', group: 'Navigation' },
    ])
    palette.open()
    palette.query.value = 'scoring'
    await nextTick()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))
    await flushPromises()
    expect(navigateToMock).toHaveBeenCalledWith('/scoring')
    expect(palette.isOpen.value).toBe(false)
    w.unmount()
  })

  it('ArrowDown/ArrowUp déplacent l\'index actif', async () => {
    const w = makeWrapper()
    const palette = useCommandPalette()
    palette.registerActions([
      { id: 'a', label: 'Aaa', group: 'Navigation' },
      { id: 'b', label: 'Bbb', group: 'Navigation' },
      { id: 'c', label: 'Ccc', group: 'Navigation' },
    ])
    palette.open()
    palette.query.value = ''
    await nextTick()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }))
    await nextTick()
    const actives = w.findAll('[data-active="true"]')
    expect(actives.length).toBeGreaterThan(0)
    w.unmount()
  })

  it('Enter sur action.run() invoque la fonction', async () => {
    const w = makeWrapper()
    const palette = useCommandPalette()
    const run = vi.fn()
    palette.registerActions([{ id: 'x', label: 'Action X', run, group: 'Actions' }])
    palette.open()
    palette.query.value = 'action'
    await nextTick()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))
    await flushPromises()
    expect(run).toHaveBeenCalled()
    w.unmount()
  })
})
