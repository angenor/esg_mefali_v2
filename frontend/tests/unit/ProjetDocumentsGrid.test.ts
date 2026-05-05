// F50 (T051) — Tests ProjetDocumentsGrid.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"

;(globalThis as { useRuntimeConfig?: unknown }).useRuntimeConfig = () => ({
  public: { apiBase: "http://api" },
})
;(globalThis as { $fetch?: unknown }).$fetch = vi.fn()

class FakeBC {
  postMessage(): void {}
  addEventListener(): void {}
  removeEventListener(): void {}
  close(): void {}
}
;(globalThis as { BroadcastChannel?: unknown }).BroadcastChannel =
  FakeBC as unknown as typeof BroadcastChannel

import ProjetDocumentsGrid from "../../app/components/documents/ProjetDocumentsGrid.vue"
import { useDocumentsStore } from "../../app/stores/documents"
import type { DocumentDetail } from "../../app/types/documents"

function makeDoc(p: Partial<DocumentDetail> & Pick<DocumentDetail, "id" | "name">): DocumentDetail {
  return {
    entreprise_id: "e",
    original_filename: p.name,
    mime_type: "application/pdf",
    size_bytes: 12345,
    type: "statuts",
    ocr_status: "done",
    ocr_error: null,
    created_at: "2026-04-30T15:00:00Z",
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

async function mountComp(opts: {
  storedDocs?: DocumentDetail[]
  storedByProjet?: string[]
  projetName?: string
} = {}) {
  setActivePinia(createPinia())
  const store = useDocumentsStore()
  vi.spyOn(store, "fetchProjet").mockResolvedValue(undefined)
  vi.spyOn(store, "fetchEntreprise").mockResolvedValue(undefined)

  for (const d of opts.storedDocs ?? []) {
    store.items[d.id] = d
  }
  if (opts.storedByProjet) {
    store.byProjet["p1"] = opts.storedByProjet
  }

  const wrapper = mount(ProjetDocumentsGrid, {
    props: { projetId: "p1", projetName: opts.projetName },
    global: {
      stubs: {
        UploadZone: true,
      },
    },
  })
  await flushPromises()
  return { wrapper, store }
}

describe("<ProjetDocumentsGrid> (F50)", () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("affiche l'empty state projet quand aucun doc lié", async () => {
    const { wrapper } = await mountComp({ projetName: "Solaire" })
    expect(wrapper.text()).toContain("Solaire")
    // Bouton CTA "Ajouter au projet" issu de DocumentEmptyState.
    expect(wrapper.text()).toContain("Ajouter au projet")
  })

  it("affiche la grille de docs liés", async () => {
    const docs = [
      makeDoc({ id: "d1", name: "Statuts.pdf" }),
      makeDoc({ id: "d2", name: "Devis.pdf", type: "facture" }),
    ]
    const { wrapper } = await mountComp({
      storedDocs: docs,
      storedByProjet: ["d1", "d2"],
    })
    expect(wrapper.text()).toContain("Statuts.pdf")
    expect(wrapper.text()).toContain("Devis.pdf")
    // Tous les docs ont le bouton "Retirer du projet".
    const removeBtns = wrapper
      .findAll("button")
      .filter((b) => b.text() === "Retirer du projet")
    expect(removeBtns).toHaveLength(2)
  })

  it("toggle « Lier un document existant » affiche le picker et liste les candidats", async () => {
    const { wrapper, store } = await mountComp({
      storedDocs: [
        makeDoc({ id: "x1", name: "Cand-A" }),
        makeDoc({ id: "x2", name: "Cand-B" }),
      ],
      storedByProjet: [],
    })
    await wrapper
      .findAll("button")
      .find((b) => b.text() === "Lier un document existant")!
      .trigger("click")
    expect(wrapper.text()).toContain("Cand-A")
    expect(wrapper.text()).toContain("Cand-B")

    // Clic sur Lier appelle store.linkProjet.
    const linkSpy = vi.spyOn(store, "linkProjet").mockResolvedValue(undefined)
    const lierA = wrapper
      .findAll("li")
      .find((li) => li.text().includes("Cand-A"))!
      .find("button")
    await lierA.trigger("click")
    await flushPromises()
    expect(linkSpy).toHaveBeenCalledWith("x1", "p1")
  })

  it("affiche un message si aucun candidat à lier", async () => {
    const { wrapper } = await mountComp()
    await wrapper
      .findAll("button")
      .find((b) => b.text() === "Lier un document existant")!
      .trigger("click")
    expect(wrapper.text()).toContain("Aucun document disponible")
  })

  it("affiche linkError en role=alert quand store.linkProjet rejette", async () => {
    const { wrapper, store } = await mountComp({
      storedDocs: [makeDoc({ id: "f1", name: "F" })],
      storedByProjet: [],
    })
    vi.spyOn(store, "linkProjet").mockRejectedValueOnce(new Error("boom"))
    await wrapper
      .findAll("button")
      .find((b) => b.text() === "Lier un document existant")!
      .trigger("click")
    await wrapper
      .findAll("li")
      .find((li) => li.text().includes("F"))!
      .find("button")
      .trigger("click")
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain("boom")
  })

  it("Retirer du projet appelle store.unlinkProjet après confirmation", async () => {
    const { wrapper, store } = await mountComp({
      storedDocs: [makeDoc({ id: "rm-1", name: "Rm" })],
      storedByProjet: ["rm-1"],
    })
    const unlinkSpy = vi.spyOn(store, "unlinkProjet").mockResolvedValue(undefined)
    vi.spyOn(window, "confirm").mockReturnValue(true)
    await wrapper
      .findAll("button")
      .find((b) => b.text() === "Retirer du projet")!
      .trigger("click")
    expect(unlinkSpy).toHaveBeenCalledWith("rm-1", "p1")
  })

  it("ne unlink pas si l'utilisateur annule la confirmation", async () => {
    const { wrapper, store } = await mountComp({
      storedDocs: [makeDoc({ id: "rm-2", name: "Rm" })],
      storedByProjet: ["rm-2"],
    })
    const unlinkSpy = vi.spyOn(store, "unlinkProjet")
    vi.spyOn(window, "confirm").mockReturnValue(false)
    await wrapper
      .findAll("button")
      .find((b) => b.text() === "Retirer du projet")!
      .trigger("click")
    expect(unlinkSpy).not.toHaveBeenCalled()
  })

  it("toggle Téléverser affiche/masque l'UploadZone", async () => {
    const { wrapper } = await mountComp()
    const tlvBtn = wrapper.findAll("button").find((b) => b.text() === "Téléverser")
    await tlvBtn!.trigger("click")
    expect(wrapper.text()).toContain("Masquer")
  })
})
