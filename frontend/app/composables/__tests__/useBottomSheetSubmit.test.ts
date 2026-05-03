import { describe, expect, it, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useBottomSheetSubmit } from '../useBottomSheetSubmit'

const fetchMock = vi.fn()
beforeEach(() => {
  setActivePinia(createPinia())
  fetchMock.mockReset()
  ;(globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch
})

const baseArgs = {
  threadId: 't1',
  inResponseToMessageId: 'm1',
  tool: 'ask_yes_no' as const,
  value: true,
  label: 'Oui',
}

describe('useBottomSheetSubmit', () => {
  it('renvoie ok=true sur 200', async () => {
    fetchMock.mockResolvedValue(new Response('{"id":"x"}', { status: 200 }))
    const s = useBottomSheetSubmit()
    const res = await s.submit(baseArgs)
    expect(res.ok).toBe(true)
    expect(res.status).toBe(200)
  })

  it('mappe 409 en silencieux (ok=false, errorCode=409)', async () => {
    fetchMock.mockResolvedValue(new Response('', { status: 409 }))
    const s = useBottomSheetSubmit()
    const res = await s.submit(baseArgs)
    expect(res.ok).toBe(false)
    expect(res.errorCode).toBe('409')
  })

  it('mappe 422 en erreur inline', async () => {
    fetchMock.mockResolvedValue(new Response('', { status: 422 }))
    const s = useBottomSheetSubmit()
    const res = await s.submit(baseArgs)
    expect(res.ok).toBe(false)
    expect(res.errorCode).toBe('422')
  })

  it('mappe 503 en 5xx retriable', async () => {
    fetchMock.mockResolvedValue(new Response('', { status: 503 }))
    const s = useBottomSheetSubmit()
    const res = await s.submit(baseArgs)
    expect(res.errorCode).toBe('5xx')
  })

  it('bloque la double-soumission via inFlight', async () => {
    let resolveFetch: ((v: Response) => void) | null = null
    fetchMock.mockImplementation(
      () => new Promise<Response>((resolve) => { resolveFetch = resolve }),
    )
    const s = useBottomSheetSubmit()
    const first = s.submit(baseArgs)
    const second = await s.submit(baseArgs)
    expect(second.ok).toBe(false)
    expect(second.errorCode).toBe('409')
    resolveFetch?.(new Response('{}', { status: 200 }))
    await first
  })

  it('mappe une erreur réseau (fetch reject) en code "network"', async () => {
    fetchMock.mockRejectedValue(new Error('network down'))
    const s = useBottomSheetSubmit()
    const res = await s.submit(baseArgs)
    expect(res.errorCode).toBe('network')
  })
})
