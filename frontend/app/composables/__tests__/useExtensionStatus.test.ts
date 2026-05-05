// F52 US5 — Tests Vitest du composable useExtensionStatus.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useExtensionStatus } from '../useExtensionStatus'

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
  // eslint-disable-next-line no-var
  var useCsrf: unknown
}

describe('useExtensionStatus', () => {
  beforeEach(() => {
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: 'http://api' } })
    globalThis.useCsrf = () => ({ withCsrf: () => ({}) })
    delete (globalThis as unknown as { chrome?: unknown }).chrome
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('refresh() peuple state avec detected=true', async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue({
      detected: true,
      extension_version: '0.4.2',
      last_ping_at: '2026-05-05T12:00:00Z',
    })
    const flow = useExtensionStatus()
    await flow.refresh()
    expect(flow.state.value.status.detected).toBe(true)
    expect(flow.state.value.status.extension_version).toBe('0.4.2')
  })

  it("refresh() expose detected=false si l'API renvoie un payload neutre", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue({
      detected: false,
      extension_version: null,
      last_ping_at: null,
    })
    const flow = useExtensionStatus()
    await flow.refresh()
    expect(flow.state.value.status.detected).toBe(false)
  })

  it('refresh() pose error en cas d\'échec', async () => {
    globalThis.$fetch = vi.fn().mockRejectedValue(new Error('network'))
    const flow = useExtensionStatus()
    await flow.refresh()
    expect(flow.state.value.error).toBe('network')
  })

  it('forcePing() utilise chrome.runtime quand disponible', async () => {
    const sendMock = vi.fn().mockResolvedValue({ ok: true })
    ;(globalThis as unknown as { chrome: object }).chrome = {
      runtime: { sendMessage: sendMock },
    }
    const fetchMock = vi.fn().mockResolvedValue({
      detected: true,
      extension_version: '0.4.2',
      last_ping_at: '2026-05-05T12:00:00Z',
    })
    globalThis.$fetch = fetchMock
    vi.useFakeTimers()
    const flow = useExtensionStatus()
    const promise = flow.forcePing()
    await Promise.resolve()
    expect(sendMock).toHaveBeenCalledWith({
      type: 'FORCE_PING',
      payload: {},
    })
    await vi.runAllTimersAsync()
    await promise
    vi.useRealTimers()
  })

  it('forcePing() tombe en fallback POST si chrome.runtime indisponible', async () => {
    const fetchMock = vi
      .fn()
      // POST /me/extension/ping
      .mockResolvedValueOnce({ ok: true })
      // refresh suivant
      .mockResolvedValueOnce({
        detected: true,
        extension_version: '0.0.0',
        last_ping_at: '2026-05-05T12:00:00Z',
      })
    globalThis.$fetch = fetchMock
    const flow = useExtensionStatus()
    await flow.forcePing()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
