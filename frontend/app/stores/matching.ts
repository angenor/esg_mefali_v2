// F51 T013 — Store Pinia useMatchingStore.
//
// Source de vérité UI pour la page `/matching` :
// - filtres URL-persisted (via composable useMatchingFilters)
// - liste d'offres (scorée si `projetActifId`, sinon catalogue global)
// - drawer offre courante
// - état carte Leaflet

import { defineStore } from "pinia"
import { matchingApi } from "~/services/api/matching"
import { offresApi } from "~/services/api/offres"
import type {
  MatchingFilters,
  OffreDetail,
  OffreListItem,
  OffreMatchItem,
} from "~/types/matching"

export type OffreItem = OffreMatchItem | OffreListItem

interface State {
  projetActifId: string | null
  filters: MatchingFilters
  offres: OffreItem[]
  loading: boolean
  error: string | null
  carteVisible: boolean
  drawerOffreId: string | null
  drawerOffre: OffreDetail | null
  drawerLoading: boolean
}

export const useMatchingStore = defineStore("matching", {
  state: (): State => ({
    projetActifId: null,
    filters: {},
    offres: [],
    loading: false,
    error: null,
    carteVisible: false,
    drawerOffreId: null,
    drawerOffre: null,
    drawerLoading: false,
  }),

  getters: {
    hasResults: (s) => s.offres.length > 0,
    isScoredMode: (s) => s.projetActifId !== null,
  },

  actions: {
    setProjetActif(projetId: string | null): void {
      this.projetActifId = projetId
    },

    setFilters(filters: MatchingFilters): void {
      this.filters = { ...filters }
    },

    async fetchOffres(): Promise<void> {
      this.loading = true
      this.error = null
      try {
        if (this.projetActifId) {
          const out = await matchingApi.listProjetMatching(
            this.projetActifId,
            50,
          )
          // Apply client-side filtering pour les filtres non couverts par le matching backend.
          this.offres = applyClientFilters(out.items, this.filters)
        } else {
          const out = await offresApi.list({ ...this.filters, limit: 50 })
          this.offres = out.items
        }
      } catch (err) {
        this.error = (err as Error).message ?? "fetch_failed"
        this.offres = []
      } finally {
        this.loading = false
      }
    },

    async openDrawer(offreId: string): Promise<void> {
      this.drawerOffreId = offreId
      this.drawerLoading = true
      this.drawerOffre = null
      try {
        this.drawerOffre = await offresApi.getDetail(offreId)
      } catch (err) {
        this.error = (err as Error).message ?? "drawer_load_failed"
      } finally {
        this.drawerLoading = false
      }
    },

    closeDrawer(): void {
      this.drawerOffreId = null
      this.drawerOffre = null
    },

    toggleCarte(visible?: boolean): void {
      this.carteVisible = visible ?? !this.carteVisible
    },

    reset(): void {
      this.offres = []
      this.error = null
      this.drawerOffreId = null
      this.drawerOffre = null
    },
  },
})

function applyClientFilters(
  items: OffreMatchItem[],
  filters: MatchingFilters,
): OffreMatchItem[] {
  return items.filter((it) => {
    if (filters.type && it.type !== filters.type) return false
    if (filters.intermediaire_id && it.intermediaire.id !== filters.intermediaire_id)
      return false
    if (filters.secteur && !it.secteurs.includes(filters.secteur)) return false
    if (filters.duree_min_mois !== undefined && it.duree_max_mois < filters.duree_min_mois)
      return false
    if (filters.duree_max_mois !== undefined && it.duree_min_mois > filters.duree_max_mois)
      return false
    return true
  })
}
