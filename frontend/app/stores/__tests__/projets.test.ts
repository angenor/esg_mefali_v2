// F43 T012 — tests vitest store projets (list, create, patch 200/409/422, softDelete).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { createPinia, setActivePinia } from "pinia"
import { useProjetsStore, type ProjetRead } from "../projets"

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

function makeProjet(overrides: Partial<ProjetRead> = {}): ProjetRead {
  return {
    id: "p-1",
    account_id: "acc-1",
    version: 2,
    nom: "Projet solaire",
    statut: "brouillon",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
    ...overrides,
  }
}

class FetchError extends Error {
  statusCode: number
  data: unknown
  constructor(status: number, data: unknown) {
    super(`HTTP ${status}`)
    this.statusCode = status
    this.data = data
  }
}

describe("useProjetsStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: "http://api" } })
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("loadList stocke la liste", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue({
      items: [{ id: "p-1", nom: "X", statut: "brouillon", updated_at: "x" }],
      total: 1,
    })
    const store = useProjetsStore()
    await store.loadList()
    expect(store.list).toHaveLength(1)
    expect(store.loaded).toBe(true)
  })

  it("create insère en tête de liste et stocke le détail", async () => {
    const created = makeProjet({ id: "p-new" })
    globalThis.$fetch = vi.fn().mockResolvedValue(created)
    const store = useProjetsStore()
    const result = await store.create({ nom: "Projet solaire" })
    expect(result.id).toBe("p-new")
    expect(store.list[0]?.id).toBe("p-new")
    expect(store.versionById["p-new"]).toBe(2)
  })

  it("patchField 200 met à jour byId + version", async () => {
    const updated = makeProjet({ version: 3, nom: "Projet hydro" })
    globalThis.$fetch = vi.fn().mockResolvedValue(updated)
    const store = useProjetsStore()
    store.applyDetail(makeProjet())
    const res = await store.patchField("p-1", "nom", "Projet hydro")
    expect(res.ok).toBe(true)
    expect(store.versionById["p-1"]).toBe(3)
  })

  it("patchField 409 set le conflit dans le store", async () => {
    globalThis.$fetch = vi
      .fn()
      .mockRejectedValue(
        new FetchError(409, { code: "version_conflict", current_version: 5, nom: "Chat value" }),
      )
    const store = useProjetsStore()
    store.applyDetail(makeProjet())
    const res = await store.patchField("p-1", "nom", "Mon nom")
    expect(res.ok).toBe(false)
    if (!res.ok) expect(res.error).toBe("conflict")
    expect(store.conflicts["p-1"]?.field).toBe("nom")
    expect(store.conflicts["p-1"]?.current_version).toBe(5)
  })

  it("patchField 422 set l'erreur de validation", async () => {
    globalThis.$fetch = vi
      .fn()
      .mockRejectedValue(new FetchError(422, { detail: [{ msg: "invalid" }] }))
    const store = useProjetsStore()
    store.applyDetail(makeProjet())
    const res = await store.patchField("p-1", "nom", "")
    expect(res.ok).toBe(false)
    if (!res.ok) expect(res.error).toBe("validation")
    expect(store.errors["p-1"]?.nom).toBe("invalid")
  })

  it("patchField réseau set l'erreur 'network'", async () => {
    globalThis.$fetch = vi.fn().mockRejectedValue(new Error("net down"))
    const store = useProjetsStore()
    store.applyDetail(makeProjet())
    const res = await store.patchField("p-1", "nom", "X")
    expect(res.ok).toBe(false)
    if (!res.ok) expect(res.error).toBe("network")
  })

  it("softDelete marque deleted_at sur la liste active", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue(undefined)
    const store = useProjetsStore()
    store.list = [
      { id: "p-1", nom: "X", statut: "brouillon", updated_at: "now" },
    ]
    const ok = await store.softDelete("p-1")
    expect(ok).toBe(true)
    expect(store.list[0]?.deleted_at).toBeTruthy()
    expect(store.activeList).toHaveLength(0)
  })
})
