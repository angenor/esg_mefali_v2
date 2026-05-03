// F43 T012 — tests vitest store entreprise (loadAll, conflict, errors).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { createPinia, setActivePinia } from "pinia"
import { useEntrepriseStore } from "../entreprise"

declare global {
  // Nuxt-injected helpers — on les déclare ici pour les besoins du test.
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

const ENTREPRISE_FIXTURE = {
  id: "ent-1",
  account_id: "acc-1",
  version: 3,
  raison_sociale: "ACME SARL",
}
const COMPLETENESS_FIXTURE = {
  percentage: 42,
  missing_required_for_features: [
    { feature_code: "scoring_esg", missing_fields: ["secteur_principal"] },
  ],
}

describe("useEntrepriseStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: "http://api" } })
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("loadAll récupère entreprise + completeness en parallèle", async () => {
    globalThis.$fetch = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith("/me/entreprise")) return Promise.resolve(ENTREPRISE_FIXTURE)
      if (url.endsWith("/me/entreprise/completeness")) return Promise.resolve(COMPLETENESS_FIXTURE)
      return Promise.reject(new Error(`unexpected ${url}`))
    })
    const store = useEntrepriseStore()
    await store.loadAll()
    expect(store.data?.id).toBe("ent-1")
    expect(store.version).toBe(3)
    expect(store.completion?.percentage).toBe(42)
    expect(store.completionPct).toBe(42) // compat F42
    expect(store.loaded).toBe(true)
  })

  it("setConflict / clearPendingChange mutent l'agrégat", () => {
    const store = useEntrepriseStore()
    store.setConflict({ field: "raison_sociale", your: "A", current: "B", current_version: 5 })
    expect(store.conflict?.field).toBe("raison_sociale")
    store.setPendingChange("raison_sociale", "draft")
    expect(store.pendingChanges.raison_sociale).toBe("draft")
    store.clearPendingChange("raison_sociale")
    expect(store.pendingChanges.raison_sociale).toBeUndefined()
  })

  it("loadCompletion (compat F42) renvoie 0 sur erreur", async () => {
    globalThis.$fetch = vi.fn().mockRejectedValue(new Error("boom"))
    const store = useEntrepriseStore()
    const pct = await store.loadCompletion()
    expect(pct).toBe(0)
  })

  it("reset remet l'état à zéro", () => {
    const store = useEntrepriseStore()
    store.applyData(ENTREPRISE_FIXTURE)
    store.reset()
    expect(store.data).toBeNull()
    expect(store.version).toBeNull()
  })
})
