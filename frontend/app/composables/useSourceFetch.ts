/**
 * F03 US4 — useSourceFetch(id) : récupère une Source via GET /sources/{id}.
 *
 * Lecture publique unitaire (FR-004). Renvoie loading/data/error.
 */
import { ref } from 'vue'

export interface Source {
  id: string
  url: string
  title: string
  publisher: string
  version: string | null
  date_publi: string | null
  page: string | null
  section: string | null
  captured_at: string
  verified_at: string | null
  verification_status: 'pending' | 'verified' | 'outdated' | 'rejected'
  notes: string | null
}

export interface SourceFetchState {
  data: Source | null
  loading: boolean
  error: string | null
}

const API_BASE
  = (typeof process !== 'undefined' && process.env?.NUXT_PUBLIC_API_BASE)
    || 'http://localhost:8000'

export function useSourceFetch(id: string) {
  const state = ref<SourceFetchState>({
    data: null,
    loading: true,
    error: null,
  })

  const fetchSource = async () => {
    state.value.loading = true
    state.value.error = null
    try {
      const res = await fetch(`${API_BASE}/sources/${id}`, {
        credentials: 'include',
      })
      if (!res.ok) {
        state.value.error = res.status === 404 ? 'Source introuvable' : `Erreur ${res.status}`
        state.value.data = null
        return
      }
      state.value.data = (await res.json()) as Source
    }
    catch (e) {
      state.value.error = e instanceof Error ? e.message : 'Erreur réseau'
      state.value.data = null
    }
    finally {
      state.value.loading = false
    }
  }

  fetchSource()
  return { state, refresh: fetchSource }
}
