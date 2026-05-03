// F42 T060 — Store entreprise (lazy load completion %)
import { defineStore } from "pinia"

interface CompletenessOut {
  percentage: number
  missing_required_for_features: Array<{ feature_code: string; missing_fields: string[] }>
}

export const useEntrepriseStore = defineStore("entreprise", {
  state: () => ({
    completionPct: null as number | null,
    loaded: false as boolean,
    loading: false as boolean,
  }),
  actions: {
    async loadCompletion(): Promise<number | null> {
      if (this.loading) return this.completionPct
      this.loading = true
      try {
        const config = useRuntimeConfig()
        const apiBase = config.public.apiBase as string
        const data = await $fetch<CompletenessOut>(`${apiBase}/me/entreprise/completeness`, {
          credentials: "include",
        })
        this.completionPct = data.percentage
        this.loaded = true
        return this.completionPct
      } catch {
        // Fail-safe: si endpoint indisponible, on retourne 0 (déclenchera l'empty state)
        this.completionPct = 0
        this.loaded = true
        return 0
      } finally {
        this.loading = false
      }
    },
    reset() {
      this.completionPct = null
      this.loaded = false
      this.loading = false
    },
  },
})
