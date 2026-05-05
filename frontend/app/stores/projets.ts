// F43 T011 — Store projets (liste + détail + version optimiste).
import { defineStore } from "pinia"
import type { MoneyOut, ConflictBlock } from "./entreprise"

export type ProjetStatut =
  | "brouillon"
  | "en_recherche_financement"
  | "finance"
  | "en_execution"
  | "cloture"

export type TypeImpact =
  | "mitigation_carbone"
  | "adaptation_climat"
  | "biodiversite"
  | "economie_circulaire"
  | "social"
  | "autre"

export type StructureFinancement =
  | "subvention"
  | "pret_concessionnel"
  | "equity"
  | "blending"

export type Maturite = "ideation" | "prototype" | "pilote" | "deploiement" | "replication"

export interface ProjetSummary {
  id: string
  nom: string
  statut: ProjetStatut
  secteur?: string | null
  score_esg?: number | null
  has_active_candidature?: boolean
  updated_at: string
  deleted_at?: string | null
}

export interface ProjetRead {
  id: string
  account_id: string
  version: number
  nom: string
  description?: string | null
  secteur?: string | null
  type_impact?: TypeImpact | null
  localisation_pays_iso2?: string | null
  localisation_region?: string | null
  localisation_lat?: string | null
  localisation_lng?: string | null
  budget?: MoneyOut | null
  horizon_mois?: number | null
  maturite?: Maturite | null
  structure_financement?: StructureFinancement | null
  statut: ProjetStatut
  score_esg?: number | null
  has_active_candidature?: boolean
  created_at: string
  updated_at: string
  deleted_at?: string | null
}

export interface ProjetCreate {
  nom: string
  description?: string
  secteur?: string
  type_impact?: TypeImpact
  localisation_pays_iso2?: string
  localisation_region?: string
  localisation_lat?: string
  localisation_lng?: string
  budget?: MoneyOut
  horizon_mois?: number
}

export interface DocumentProjetRead {
  id: string
  projet_id: string
  nom: string
  mime: string
  taille_octets: number
  type_doc: string
  created_at: string
}

interface ProjetsState {
  list: ProjetSummary[]
  byId: Record<string, ProjetRead>
  versionById: Record<string, number>
  documentsById: Record<string, DocumentProjetRead[]>
  loading: boolean
  loaded: boolean
  saving: Record<string, Record<string, boolean>>
  errors: Record<string, Record<string, string | null>>
  conflicts: Record<string, ConflictBlock | null>
}

export const useProjetsStore = defineStore("projets", {
  state: (): ProjetsState => ({
    list: [],
    byId: {},
    versionById: {},
    documentsById: {},
    loading: false,
    loaded: false,
    saving: {},
    errors: {},
    conflicts: {},
  }),
  getters: {
    activeList: (state) =>
      state.list.filter((p) => !p.deleted_at),
    getById: (state) => (id: string) => state.byId[id] ?? null,
  },
  actions: {
    async loadList(): Promise<void> {
      if (this.loading) return
      this.loading = true
      try {
        const config = useRuntimeConfig()
        const apiBase = config.public.apiBase as string
        const data = await $fetch<{ items: ProjetSummary[]; total: number }>(
          `${apiBase}/me/projets`,
          { credentials: "include" },
        )
        this.list = data.items
        this.loaded = true
      } finally {
        this.loading = false
      }
    },

    async loadOne(id: string): Promise<ProjetRead | null> {
      const config = useRuntimeConfig()
      const apiBase = config.public.apiBase as string
      try {
        const [projet, documents] = await Promise.all([
          $fetch<ProjetRead>(`${apiBase}/me/projets/${id}`, { credentials: "include" }),
          $fetch<DocumentProjetRead[]>(`${apiBase}/me/projets/${id}/documents`, {
            credentials: "include",
          }).catch(() => [] as DocumentProjetRead[]),
        ])
        this.applyDetail(projet)
        this.documentsById = { ...this.documentsById, [id]: documents }
        return projet
      } catch {
        return null
      }
    },

    applyDetail(projet: ProjetRead): void {
      this.byId = { ...this.byId, [projet.id]: projet }
      this.versionById = { ...this.versionById, [projet.id]: projet.version }
    },

    async create(payload: ProjetCreate): Promise<ProjetRead> {
      const config = useRuntimeConfig()
      const apiBase = config.public.apiBase as string
      const created = await $fetch<ProjetRead>(`${apiBase}/me/projets`, {
        method: "POST",
        credentials: "include",
        body: payload,
      })
      this.applyDetail(created)
      // Mise à jour du résumé en tête de liste.
      this.list = [
        {
          id: created.id,
          nom: created.nom,
          statut: created.statut,
          secteur: created.secteur ?? null,
          score_esg: created.score_esg ?? null,
          has_active_candidature: created.has_active_candidature ?? false,
          updated_at: created.updated_at,
          deleted_at: created.deleted_at ?? null,
        },
        ...this.list,
      ]
      return created
    },

    async patchField<T = unknown>(
      id: string,
      field: string,
      value: T,
    ): Promise<{ ok: true; data: ProjetRead } | { ok: false; error: "conflict" | "validation" | "network"; payload?: unknown }> {
      const version = this.versionById[id]
      if (version == null) return { ok: false, error: "validation", payload: "missing_version" }
      this.setSaving(id, field, true)
      try {
        const config = useRuntimeConfig()
        const apiBase = config.public.apiBase as string
        const updated = await $fetch<ProjetRead>(`${apiBase}/me/projets/${id}`, {
          method: "PATCH",
          credentials: "include",
          body: { [field]: value, version },
        })
        this.applyDetail(updated)
        this.setError(id, field, null)
        this.setConflict(id, null)
        return { ok: true, data: updated }
      } catch (err: unknown) {
        return this.handlePatchError(id, field, value, err)
      } finally {
        this.setSaving(id, field, false)
      }
    },

    handlePatchError(
      id: string,
      field: string,
      value: unknown,
      err: unknown,
    ):
      | { ok: false; error: "conflict" | "validation" | "network"; payload?: unknown } {
      // $fetch attache `status` sur l'erreur ($fetch FetchError).
      const status = (err as { statusCode?: number; status?: number })?.statusCode
        ?? (err as { status?: number })?.status
      if (status === 409) {
        const data = (err as { data?: { current_version: number; [key: string]: unknown } }).data
        this.setConflict(id, {
          field,
          your: value,
          current: data?.[field] ?? null,
          current_version: data?.current_version ?? this.versionById[id] ?? 0,
        })
        return { ok: false, error: "conflict", payload: data }
      }
      if (status === 422) {
        const detail = (err as { data?: { detail?: unknown } }).data?.detail
        const message = Array.isArray(detail)
          ? String((detail[0] as { msg?: string })?.msg ?? "validation")
          : "validation"
        this.setError(id, field, message)
        return { ok: false, error: "validation", payload: detail }
      }
      this.setError(id, field, "network")
      return { ok: false, error: "network" }
    },

    async softDelete(id: string): Promise<boolean> {
      const config = useRuntimeConfig()
      const apiBase = config.public.apiBase as string
      try {
        await $fetch(`${apiBase}/me/projets/${id}`, {
          method: "DELETE",
          credentials: "include",
        })
        // Soft delete : on retire de la liste active.
        this.list = this.list.map((p) =>
          p.id === id ? { ...p, deleted_at: new Date().toISOString() } : p,
        )
        return true
      } catch {
        return false
      }
    },

    setSaving(id: string, field: string, value: boolean): void {
      const current = this.saving[id] ?? {}
      this.saving = { ...this.saving, [id]: { ...current, [field]: value } }
    },

    setError(id: string, field: string, message: string | null): void {
      const current = this.errors[id] ?? {}
      this.errors = { ...this.errors, [id]: { ...current, [field]: message } }
    },

    setConflict(id: string, conflict: ConflictBlock | null): void {
      this.conflicts = { ...this.conflicts, [id]: conflict }
    },

    reset(): void {
      this.list = []
      this.byId = {}
      this.versionById = {}
      this.documentsById = {}
      this.loading = false
      this.loaded = false
      this.saving = {}
      this.errors = {}
      this.conflicts = {}
    },
  },
})
