// F40 T010 — useSourcesStore : cache TTL 5 min + dédoublonnage des appels en vol (R3).
import { defineStore } from 'pinia'
import { SourceNotFoundError, isSourcePillar, type SourceRef } from '~/types/viz/source'

export const SOURCES_TTL_MS = 5 * 60 * 1000

interface CacheEntry {
  data: SourceRef
  fetchedAt: number
}

interface SourcesState {
  cache: Map<string, CacheEntry>
  inFlight: Map<string, Promise<SourceRef>>
}

type Fetcher = (id: string) => Promise<Response>

function defaultFetcher(): Fetcher {
  return async (id: string) => {
    const base = (typeof process !== 'undefined' && process.env?.NUXT_PUBLIC_API_BASE)
      || 'http://localhost:8010'
    return fetch(`${base}/api/sources/${encodeURIComponent(id)}`, {
      credentials: 'include',
      headers: { Accept: 'application/json' },
    })
  }
}

let injectedFetcher: Fetcher | null = null

// Mockable côté tests : remplace le transport HTTP sans toucher à la logique.
export function __setSourcesFetcher(f: Fetcher | null): void {
  injectedFetcher = f
}

function now(): number {
  return Date.now()
}

function isFresh(entry: CacheEntry | undefined): entry is CacheEntry {
  return !!entry && now() - entry.fetchedAt < SOURCES_TTL_MS
}

function validate(payload: unknown): SourceRef {
  if (!payload || typeof payload !== 'object') {
    throw new Error('SourceRef: payload non-objet')
  }
  const o = payload as Record<string, unknown>
  if (typeof o.source_id !== 'string'
    || typeof o.title !== 'string'
    || typeof o.url !== 'string'
    || typeof o.valid_from !== 'string'
    || (o.status !== 'verified' && o.status !== 'revoked')) {
    throw new Error('SourceRef: champ requis manquant ou invalide')
  }
  if (!isSourcePillar(o.pillar)) {
    // Pillar hors enum → erreur d'intégration. Le composant fera le fallback.
    // eslint-disable-next-line no-console
    console.error('[useSourcesStore] pillar inconnu, fallback neutre :', o.pillar)
  }
  return {
    source_id: o.source_id,
    title: o.title,
    url: o.url,
    pillar: isSourcePillar(o.pillar) ? o.pillar : ('methodology'),
    valid_from: o.valid_from,
    valid_to: typeof o.valid_to === 'string' ? o.valid_to : null,
    status: o.status,
    revoked_reason: typeof o.revoked_reason === 'string' ? o.revoked_reason : null,
  }
}

export const useSourcesStore = defineStore('viz-sources', {
  state: (): SourcesState => ({
    cache: new Map(),
    inFlight: new Map(),
  }),
  actions: {
    peek(source_id: string): SourceRef | undefined {
      const entry = this.cache.get(source_id)
      return isFresh(entry) ? entry.data : undefined
    },
    async resolve(source_id: string): Promise<SourceRef> {
      const cached = this.cache.get(source_id)
      if (isFresh(cached)) return cached.data

      const inflight = this.inFlight.get(source_id)
      if (inflight) return inflight

      const fetcher = injectedFetcher ?? defaultFetcher()
      const promise = (async () => {
        try {
          const res = await fetcher(source_id)
          if (res.status === 404) {
            throw new SourceNotFoundError(source_id)
          }
          if (!res.ok) {
            throw new Error(`SourceRef HTTP ${res.status}`)
          }
          const json = await res.json()
          const ref = validate(json)
          this.cache.set(source_id, { data: ref, fetchedAt: now() })
          return ref
        }
        finally {
          this.inFlight.delete(source_id)
        }
      })()

      this.inFlight.set(source_id, promise)
      return promise
    },
    invalidate(source_id?: string): void {
      if (source_id === undefined) {
        this.cache.clear()
        return
      }
      this.cache.delete(source_id)
    },
    reset(): void {
      this.cache.clear()
      this.inFlight.clear()
    },
  },
})
