// F40 T011 — useSourcesStore tests : TTL, dédoublonnage, 404, invalidate.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSourcesStore, __setSourcesFetcher, SOURCES_TTL_MS } from '~/stores/sources'
import { SourceNotFoundError } from '~/types/viz/source'

const VALID = {
  source_id: 'src_abc',
  title: 'Rapport GIEC AR6',
  url: 'https://example.org/giec.pdf',
  pillar: 'E',
  valid_from: '2024-01-01',
  status: 'verified',
}

function ok(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'content-type': 'application/json' },
  })
}

describe('useSourcesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    __setSourcesFetcher(null)
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
    __setSourcesFetcher(null)
  })

  it('TTL : 2e appel < 5 min utilise le cache', async () => {
    const fetcher = vi.fn(async () => ok(VALID))
    __setSourcesFetcher(fetcher)
    const store = useSourcesStore()

    await store.resolve('src_abc')
    vi.advanceTimersByTime(SOURCES_TTL_MS - 1000)
    await store.resolve('src_abc')

    expect(fetcher).toHaveBeenCalledTimes(1)
  })

  it('TTL : 2e appel après expiration refait un fetch', async () => {
    const fetcher = vi.fn(async () => ok(VALID))
    __setSourcesFetcher(fetcher)
    const store = useSourcesStore()

    await store.resolve('src_abc')
    vi.advanceTimersByTime(SOURCES_TTL_MS + 1)
    await store.resolve('src_abc')

    expect(fetcher).toHaveBeenCalledTimes(2)
  })

  it('dédoublonne les requêtes en vol concurrentes', async () => {
    let resolveFn: (r: Response) => void = () => {}
    const fetcher = vi.fn(() => new Promise<Response>((r) => { resolveFn = r }))
    __setSourcesFetcher(fetcher)
    const store = useSourcesStore()

    const p1 = store.resolve('src_abc')
    const p2 = store.resolve('src_abc')
    expect(fetcher).toHaveBeenCalledTimes(1)

    resolveFn(ok(VALID))
    const [r1, r2] = await Promise.all([p1, p2])
    expect(r1).toBe(r2)
  })

  it('propage SourceNotFoundError sur 404', async () => {
    __setSourcesFetcher(async () => new Response('{}', { status: 404 }))
    const store = useSourcesStore()
    await expect(store.resolve('missing')).rejects.toBeInstanceOf(SourceNotFoundError)
  })

  it('peek() retourne undefined si non-cache, et la valeur si frais', async () => {
    __setSourcesFetcher(async () => ok(VALID))
    const store = useSourcesStore()
    expect(store.peek('src_abc')).toBeUndefined()
    await store.resolve('src_abc')
    expect(store.peek('src_abc')).toMatchObject({ source_id: 'src_abc' })
  })

  it('invalidate ciblé purge une entrée, invalidate global purge tout', async () => {
    __setSourcesFetcher(async () => ok(VALID))
    const store = useSourcesStore()
    await store.resolve('src_abc')
    store.invalidate('src_abc')
    expect(store.peek('src_abc')).toBeUndefined()

    await store.resolve('src_abc')
    store.invalidate()
    expect(store.peek('src_abc')).toBeUndefined()
  })

  it('rejette les payloads invalides', async () => {
    __setSourcesFetcher(async () => ok({ source_id: 'x' }))
    const store = useSourcesStore()
    await expect(store.resolve('x')).rejects.toThrow()
  })
})
