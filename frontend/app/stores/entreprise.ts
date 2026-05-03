// F43 T010 — Store entreprise étendu (data + version + autosave + conflict).
//
// Rétro-compatibilité F42 :
//   - `completionPct` reste lisible directement.
//   - `loadCompletion()` continue d'exister et délègue à `loadAll()`.
//
// Nouveautés F43 :
//   - `data: EntrepriseRead | null` — agrégat de profil.
//   - `version: number | null` — concurrence optimiste (PATCH envoie `version`).
//   - `saving / errors` par champ — utilisé par `SectionCard` pour annoncer.
//   - `conflict` — set lorsque le backend retourne 409 ; consommé par
//     `ConflictDialog`.
//   - `pendingChanges` — queue d'autosave (utilisée par `useEntrepriseProfile`).
import { defineStore } from "pinia"

export interface MoneyOut {
  amount: string // Decimal sérialisé en string (P5).
  currency: "XOF" | "EUR" | "USD"
}

export interface EntrepriseRead {
  id: string
  account_id: string
  version: number
  raison_sociale?: string | null
  forme_juridique?: string | null
  secteur_principal?: string | null
  annee_creation?: number | null
  taille_ca?: MoneyOut | null
  taille_effectif?: number | null
  localisation_siege_pays_iso2?: string | null
  zones_operation_pays_iso2?: string[] | null
  gouvernance_type?: string | null
  pratiques_environnement?: string | null
  field_meta?: Record<string, EntrepriseFieldMeta> | null
  [key: string]: unknown
}

export interface EntrepriseFieldMeta {
  source_of_change?: "manual" | "llm" | "import" | "admin"
  last_updated?: string // ISO datetime
  user_id?: string | null
}

export interface MissingFeatureBlock {
  feature_code: string
  missing_fields: string[]
}

export interface CompletenessOut {
  percentage: number
  missing_required_for_features: MissingFeatureBlock[]
}

export interface ConflictBlock {
  field: string
  your: unknown
  current: unknown
  current_version: number
}

interface EntrepriseState {
  data: EntrepriseRead | null
  version: number | null
  completion: { percentage: number; missing: MissingFeatureBlock[] } | null
  /** Compat F42 — alias de `completion?.percentage`. */
  completionPct: number | null
  loaded: boolean
  loading: boolean
  saving: Record<string, boolean>
  errors: Record<string, string | null>
  conflict: ConflictBlock | null
  pendingChanges: Record<string, unknown>
}

export const useEntrepriseStore = defineStore("entreprise", {
  state: (): EntrepriseState => ({
    data: null,
    version: null,
    completion: null,
    completionPct: null,
    loaded: false,
    loading: false,
    saving: {},
    errors: {},
    conflict: null,
    pendingChanges: {},
  }),
  getters: {
    isLoaded: (state) => state.loaded,
  },
  actions: {
    /** Charge en parallèle entreprise + complétude (utilisé par useAsyncData). */
    async loadAll(): Promise<void> {
      if (this.loading) return
      this.loading = true
      try {
        const config = useRuntimeConfig()
        const apiBase = config.public.apiBase as string
        const [entreprise, completeness] = await Promise.all([
          $fetch<EntrepriseRead>(`${apiBase}/me/entreprise`, { credentials: "include" }),
          $fetch<CompletenessOut>(`${apiBase}/me/entreprise/completeness`, {
            credentials: "include",
          }),
        ])
        this.applyData(entreprise)
        this.applyCompletion(completeness)
      } finally {
        this.loaded = true
        this.loading = false
      }
    },

    /** Compat F42 — déclenche `loadAll` et retourne le pourcentage. */
    async loadCompletion(): Promise<number | null> {
      try {
        await this.loadAll()
        return this.completionPct
      } catch {
        this.completionPct = 0
        this.loaded = true
        return 0
      }
    },

    applyData(payload: EntrepriseRead): void {
      this.data = payload
      this.version = payload.version
    },

    applyCompletion(payload: CompletenessOut): void {
      this.completion = {
        percentage: payload.percentage,
        missing: payload.missing_required_for_features ?? [],
      }
      this.completionPct = payload.percentage
    },

    setSaving(field: string, value: boolean): void {
      this.saving = { ...this.saving, [field]: value }
    },

    setError(field: string, message: string | null): void {
      this.errors = { ...this.errors, [field]: message }
    },

    setConflict(conflict: ConflictBlock | null): void {
      this.conflict = conflict
    },

    setPendingChange(field: string, value: unknown): void {
      this.pendingChanges = { ...this.pendingChanges, [field]: value }
    },

    clearPendingChange(field: string): void {
      const next = { ...this.pendingChanges }
      delete next[field]
      this.pendingChanges = next
    },

    reset(): void {
      this.data = null
      this.version = null
      this.completion = null
      this.completionPct = null
      this.loaded = false
      this.loading = false
      this.saving = {}
      this.errors = {}
      this.conflict = null
      this.pendingChanges = {}
    },
  },
})
