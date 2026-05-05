// F50 (T030/T060) — Tests Pinia useDocumentsStore.
// Couvre : initial state, fetchEntreprise, enqueueUpload (dédoublonnage),
// confirmDuplicateReuse / confirmDuplicateForceNew, validateExtraction,
// softDelete, link/unlink projet, updateTags, relaunchOcr, filteredItems
// (recherche tolérante aux accents + filtre type + plage date).

import { beforeEach, describe, expect, it, vi } from "vitest"
import { createPinia, setActivePinia } from "pinia"

// Mock $fetch et useRuntimeConfig globalement (le service api/documents.ts
// utilise $fetch, et le store l'utilise via documentsApi).
const fetchMock = vi.fn()
;(globalThis as { $fetch?: unknown }).$fetch = fetchMock
;(globalThis as { useRuntimeConfig?: unknown }).useRuntimeConfig = () => ({
  public: { apiBase: "http://api" },
})

// Stub BroadcastChannel : sa structured-cloning échoue sur les Proxies Pinia
// dans le contexte happy-dom. On garde une instance no-op compatible.
class FakeBC {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  constructor(_name: string) {}
  postMessage(_data: unknown): void {}
  addEventListener(): void {}
  removeEventListener(): void {}
  close(): void {}
}
;(globalThis as { BroadcastChannel?: unknown }).BroadcastChannel = FakeBC as unknown as typeof BroadcastChannel

// Stub crypto.subtle.digest pour que useFileFingerprint ne plante pas.
// happy-dom expose un getter readonly sur ``globalThis.crypto`` ; on
// remplace seulement la propriété ``digest`` via defineProperty si besoin.
const fakeDigest = async (_alg: string, _data: ArrayBuffer) => {
  const out = new Uint8Array(32)
  out.fill(0xab)
  return out.buffer
}
if (typeof globalThis.crypto === "undefined") {
  Object.defineProperty(globalThis, "crypto", {
    configurable: true,
    value: { subtle: { digest: fakeDigest } },
  })
} else if (!globalThis.crypto.subtle) {
  Object.defineProperty(globalThis.crypto, "subtle", {
    configurable: true,
    value: { digest: fakeDigest },
  })
} else {
  // happy-dom fournit déjà subtle ; on patch digest pour la prédictibilité.
  Object.defineProperty(globalThis.crypto.subtle, "digest", {
    configurable: true,
    value: fakeDigest,
  })
}

// Mock l'upload XHR au plus simple via override de documentsApi APRÈS import.
import { documentsApi } from "../../../app/services/api/documents"
import { useDocumentsStore } from "../../../app/stores/documents"
import type { DocumentDetail, DocumentListItem } from "../../../app/types/documents"

function makeDetail(p: Partial<DocumentDetail> & Pick<DocumentDetail, "id" | "name">): DocumentDetail {
  return {
    entreprise_id: "ent1",
    original_filename: p.name,
    mime_type: "application/pdf",
    size_bytes: 1234,
    type: "statuts",
    ocr_status: "done",
    ocr_error: null,
    created_at: "2026-05-05T10:00:00Z",
    extraction_payload: { fields: [] },
    extraction_validated_at: null,
    extraction_validated_by: null,
    linked_projets: [],
    tags: [],
    deleted_at: null,
    purge_scheduled_at: null,
    ...p,
  } as DocumentDetail
}

function makeListItem(p: Partial<DocumentListItem> & Pick<DocumentListItem, "id" | "name">): DocumentListItem {
  return {
    mime_type: "application/pdf",
    size_bytes: 100,
    type: "statuts",
    created_at: "2026-05-05T09:00:00Z",
    ocr_status: "done",
    extraction_validated_at: null,
    tags: [],
    source: "document_entreprise",
    ...p,
  } as DocumentListItem
}

describe("useDocumentsStore (F50)", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchMock.mockReset()
    vi.restoreAllMocks()
  })

  it("a un état initial vide", () => {
    const s = useDocumentsStore()
    expect(s.items).toEqual({})
    expect(s.byEntreprise).toEqual([])
    expect(s.uploadQueue).toEqual([])
    expect(s.search).toEqual({ q: "", type: null, from: null, to: null })
    expect(s.entrepriseList).toEqual([])
    expect(s.loading).toBe(false)
    expect(s.error).toBe(null)
  })

  it("fetchEntreprise peuple items et byEntreprise", async () => {
    const list = [
      makeListItem({ id: "d1", name: "Statuts.pdf" }),
      makeListItem({ id: "d2", name: "Bilan.pdf", tags: ["Bilan 2024"] }),
    ]
    vi.spyOn(documentsApi, "listEntrepriseDocuments").mockResolvedValueOnce(list)
    const s = useDocumentsStore()
    await s.fetchEntreprise()
    expect(s.byEntreprise).toEqual(["d1", "d2"])
    expect(s.items["d1"]?.name).toBe("Statuts.pdf")
    expect(s.items["d2"]?.tags).toEqual(["Bilan 2024"])
    expect(s.entrepriseList.map((d) => d.id)).toEqual(["d1", "d2"])
  })

  it("fetchEntreprise pose error et lève sur échec", async () => {
    vi.spyOn(documentsApi, "listEntrepriseDocuments").mockRejectedValueOnce(
      new Error("boom"),
    )
    const s = useDocumentsStore()
    await expect(s.fetchEntreprise()).rejects.toThrow("boom")
    expect(s.error).toBe("boom")
    expect(s.loading).toBe(false)
  })

  it("upsert ajoute en tête de byEntreprise sans doublonner", () => {
    const s = useDocumentsStore()
    s.upsert(makeDetail({ id: "a", name: "A" }))
    s.upsert(makeDetail({ id: "b", name: "B" }))
    s.upsert(makeDetail({ id: "a", name: "A2" }))
    expect(s.byEntreprise).toEqual(["b", "a"])
    expect(s.items["a"]?.name).toBe("A2")
  })

  it("filteredItems applique la recherche tolérante aux accents", () => {
    const s = useDocumentsStore()
    s.upsert(makeDetail({ id: "1", name: "Bilàn 2024.pdf" }))
    s.upsert(makeDetail({ id: "2", name: "Statuts.pdf" }))
    s.upsert(makeDetail({ id: "3", name: "Inventaire.pdf", tags: ["Bilan annexe"] }))

    s.setSearch({ q: "bilan" })
    const ids = s.filteredItems.map((d) => d.id).sort()
    expect(ids).toEqual(["1", "3"])
  })

  it("filteredItems applique le filtre type", () => {
    const s = useDocumentsStore()
    s.upsert(makeDetail({ id: "1", name: "S.pdf", type: "statuts" }))
    s.upsert(makeDetail({ id: "2", name: "C.pdf", type: "contrat" }))

    s.setSearch({ type: "statuts" })
    expect(s.filteredItems.map((d) => d.id)).toEqual(["1"])
  })

  it("filteredItems applique la plage de date", () => {
    const s = useDocumentsStore()
    s.upsert(makeDetail({ id: "old", name: "O.pdf", created_at: "2025-01-01T00:00:00Z" }))
    s.upsert(makeDetail({ id: "mid", name: "M.pdf", created_at: "2026-03-15T00:00:00Z" }))
    s.upsert(makeDetail({ id: "new", name: "N.pdf", created_at: "2026-09-01T00:00:00Z" }))

    s.setSearch({ from: "2026-01-01T00:00:00Z", to: "2026-06-30T00:00:00Z" })
    expect(s.filteredItems.map((d) => d.id)).toEqual(["mid"])
  })

  it("setSearch fusionne le patch avec l'état précédent", () => {
    const s = useDocumentsStore()
    s.setSearch({ q: "x" })
    s.setSearch({ type: "statuts" })
    expect(s.search).toEqual({ q: "x", type: "statuts", from: null, to: null })
  })

  it("countByStatus agrège les ocr_status", () => {
    const s = useDocumentsStore()
    s.upsert(makeDetail({ id: "1", name: "1", ocr_status: "done" }))
    s.upsert(makeDetail({ id: "2", name: "2", ocr_status: "done" }))
    s.upsert(makeDetail({ id: "3", name: "3", ocr_status: "pending" }))
    expect(s.countByStatus).toEqual({ done: 2, pending: 1 })
  })

  it("enqueueUpload détecte un doublon via getByFingerprint et marque le job duplicate", async () => {
    vi.spyOn(documentsApi, "getByFingerprint").mockResolvedValueOnce({
      document: makeDetail({ id: "exist", name: "Existant.pdf" }),
    })
    const uploadSpy = vi.spyOn(documentsApi, "uploadDocument")
    const s = useDocumentsStore()
    const file = new File([new Uint8Array([1, 2, 3])], "x.pdf", {
      type: "application/pdf",
    })
    const job = await s.enqueueUpload(file, { type: "statuts" })

    // Laisse le runJob se résoudre.
    await new Promise((r) => setTimeout(r, 0))
    await new Promise((r) => setTimeout(r, 0))

    const found = s.uploadQueue.find((j) => j.id === job.id)
    expect(found?.status).toBe("duplicate")
    expect(uploadSpy).not.toHaveBeenCalled()
  })

  it("enqueueUpload upload réellement quand pas de doublon", async () => {
    vi.spyOn(documentsApi, "getByFingerprint").mockResolvedValueOnce(null)
    const uploaded = makeDetail({ id: "newdoc", name: "Nouveau.pdf" })
    vi.spyOn(documentsApi, "uploadDocument").mockResolvedValueOnce(uploaded)
    const s = useDocumentsStore()
    const file = new File([new Uint8Array([4, 5, 6])], "n.pdf", {
      type: "application/pdf",
    })
    const job = await s.enqueueUpload(file, { type: "statuts" })

    for (let i = 0; i < 5; i++) await new Promise((r) => setTimeout(r, 0))

    const found = s.uploadQueue.find((j) => j.id === job.id)
    expect(found?.status).toBe("success")
    expect(found?.documentId).toBe("newdoc")
    expect(s.items["newdoc"]?.name).toBe("Nouveau.pdf")
    expect(s.byEntreprise).toContain("newdoc")
  })

  it("confirmDuplicateForceNew remet le job en pending et déclenche un nouvel upload", async () => {
    // 1er enqueue : doublon détecté.
    vi.spyOn(documentsApi, "getByFingerprint").mockResolvedValueOnce({
      document: makeDetail({ id: "exist", name: "Existant.pdf" }),
    })
    // 2e passe (forceNew) : upload effectif.
    const uploaded = makeDetail({ id: "forced", name: "F.pdf" })
    vi.spyOn(documentsApi, "uploadDocument").mockResolvedValueOnce(uploaded)

    const s = useDocumentsStore()
    const file = new File([new Uint8Array([7])], "f.pdf", {
      type: "application/pdf",
    })
    const job = await s.enqueueUpload(file, { type: "statuts" })
    for (let i = 0; i < 3; i++) await new Promise((r) => setTimeout(r, 0))
    expect(s.uploadQueue.find((j) => j.id === job.id)?.status).toBe("duplicate")

    s.confirmDuplicateForceNew(job.id, { type: "statuts" })
    for (let i = 0; i < 5; i++) await new Promise((r) => setTimeout(r, 0))
    expect(s.uploadQueue.find((j) => j.id === job.id)?.status).toBe("success")
    expect(s.items["forced"]?.name).toBe("F.pdf")
  })

  it("confirmDuplicateReuse marque le job cancelled sans uploader", () => {
    const s = useDocumentsStore()
    s.uploadQueue = [
      {
        id: "j1",
        file: new File([], "x.pdf"),
        filename: "x.pdf",
        size: 0,
        mime: "application/pdf",
        sha256: null,
        percent: 0,
        status: "duplicate",
      },
    ]
    s.confirmDuplicateReuse("j1")
    expect(s.uploadQueue[0]!.status).toBe("cancelled")
  })

  it("removeJob retire le job de la queue", () => {
    const s = useDocumentsStore()
    s.uploadQueue = [
      {
        id: "j1",
        file: new File([], "x.pdf"),
        filename: "x.pdf",
        size: 0,
        mime: "application/pdf",
        sha256: null,
        percent: 0,
        status: "success",
      },
    ]
    s.removeJob("j1")
    expect(s.uploadQueue).toEqual([])
  })

  it("validateExtraction met à jour le doc et conserve les autres champs", async () => {
    vi.spyOn(documentsApi, "validateExtraction").mockResolvedValueOnce({
      id: "d1",
      extraction_validated_at: "2026-05-05T11:00:00Z",
      extraction_validated_by: "u1",
      propagated: [],
    })
    const s = useDocumentsStore()
    s.upsert(makeDetail({ id: "d1", name: "Doc.pdf" }))
    await s.validateExtraction("d1", { fields: [], propagate_to: [] })
    expect(s.items["d1"]?.extraction_validated_at).toBe("2026-05-05T11:00:00Z")
    expect(s.items["d1"]?.extraction_validated_by).toBe("u1")
    expect(s.items["d1"]?.name).toBe("Doc.pdf")
  })

  it("softDelete retire optimiste et appelle l'API", async () => {
    vi.spyOn(documentsApi, "softDelete").mockResolvedValueOnce(undefined)
    const s = useDocumentsStore()
    s.upsert(makeDetail({ id: "del", name: "X" }))
    await s.softDelete("del")
    expect(s.byEntreprise).not.toContain("del")
    expect(s.items["del"]).toBeUndefined()
  })

  it("softDelete restaure si l'API échoue", async () => {
    vi.spyOn(documentsApi, "softDelete").mockRejectedValueOnce(new Error("fail"))
    const s = useDocumentsStore()
    s.upsert(makeDetail({ id: "del", name: "X" }))
    await expect(s.softDelete("del")).rejects.toThrow("fail")
    // Doc toujours en items, byEntreprise restauré.
    expect(s.items["del"]).toBeDefined()
    expect(s.byEntreprise).toContain("del")
  })

  it("linkProjet ajoute l'id de projet et déduplique", async () => {
    vi.spyOn(documentsApi, "linkProjet").mockResolvedValue(undefined)
    const s = useDocumentsStore()
    s.upsert(makeDetail({ id: "d1", name: "X", linked_projets: [] }))
    await s.linkProjet("d1", "p1")
    expect(s.items["d1"]?.linked_projets).toEqual(["p1"])
    // Re-link même projet → pas de doublon.
    await s.linkProjet("d1", "p1")
    expect(s.items["d1"]?.linked_projets).toEqual(["p1"])
  })

  it("unlinkProjet retire l'id de projet", async () => {
    vi.spyOn(documentsApi, "unlinkProjet").mockResolvedValue(undefined)
    const s = useDocumentsStore()
    s.upsert(makeDetail({ id: "d1", name: "X", linked_projets: ["p1", "p2"] }))
    await s.unlinkProjet("d1", "p1")
    expect(s.items["d1"]?.linked_projets).toEqual(["p2"])
  })

  it("updateTags remplace la liste de tags", async () => {
    vi.spyOn(documentsApi, "updateTags").mockResolvedValueOnce(
      makeDetail({ id: "d1", name: "X", tags: ["A", "B"] }),
    )
    const s = useDocumentsStore()
    s.upsert(makeDetail({ id: "d1", name: "X", tags: ["A"] }))
    await s.updateTags("d1", ["A", "B"])
    expect(s.items["d1"]?.tags).toEqual(["A", "B"])
  })

  it("relaunchOcr passe ocr_status à processing et invalide la validation si demandé", async () => {
    vi.spyOn(documentsApi, "relaunchOcr").mockResolvedValueOnce(undefined)
    // Évite de réellement déclencher un setInterval/setTimeout via startPolling.
    const s = useDocumentsStore()
    s.startPolling = vi.fn() as never
    s.upsert(
      makeDetail({
        id: "d1",
        name: "X",
        ocr_status: "done",
        extraction_validated_at: "2026-05-05T10:00:00Z",
      }),
    )
    await s.relaunchOcr("d1", { invalidateValidation: true })
    expect(s.items["d1"]?.ocr_status).toBe("processing")
    expect(s.items["d1"]?.extraction_validated_at).toBeNull()
  })

  it("relaunchOcr ne touche PAS à validated_at si invalidateValidation=false", async () => {
    vi.spyOn(documentsApi, "relaunchOcr").mockResolvedValueOnce(undefined)
    const s = useDocumentsStore()
    s.startPolling = vi.fn() as never
    s.upsert(
      makeDetail({
        id: "d1",
        name: "X",
        ocr_status: "done",
        extraction_validated_at: "2026-05-05T10:00:00Z",
      }),
    )
    await s.relaunchOcr("d1", { invalidateValidation: false })
    expect(s.items["d1"]?.ocr_status).toBe("processing")
    expect(s.items["d1"]?.extraction_validated_at).toBe("2026-05-05T10:00:00Z")
  })
})
