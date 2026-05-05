// F50 (T034/T081) — Tests OcrSummarySheet.
// - Édition champ et émission validate avec payload conforme.
// - Bouton "Répondre librement" visible (P10).
// - Bouton Valider désactivé si already_validated.
// - Confirmation modale obligatoire si déjà validé pour relancer (T081).

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"

const fetchMock = vi.fn()
;(globalThis as { $fetch?: unknown }).$fetch = fetchMock
;(globalThis as { useRuntimeConfig?: unknown }).useRuntimeConfig = () => ({
  public: { apiBase: "http://api" },
})

class FakeBC {
  postMessage(): void {}
  addEventListener(): void {}
  removeEventListener(): void {}
  close(): void {}
}
;(globalThis as { BroadcastChannel?: unknown }).BroadcastChannel =
  FakeBC as unknown as typeof BroadcastChannel

import OcrSummarySheet from "../../app/components/documents/OcrSummarySheet.vue"
import { documentsApi } from "../../app/services/api/documents"
import { useDocumentsStore } from "../../app/stores/documents"
import type { DocumentDetail } from "../../app/types/documents"

function makeDoc(p: Partial<DocumentDetail> = {}): DocumentDetail {
  return {
    id: "doc-1",
    entreprise_id: "ent-1",
    name: "Statuts.pdf",
    original_filename: "statuts.pdf",
    mime_type: "application/pdf",
    size_bytes: 2048,
    type: "statuts",
    ocr_status: "done",
    ocr_error: null,
    created_at: "2026-04-30T15:00:00Z",
    extraction_payload: {
      fields: [
        { key: "raison_sociale", label: "Raison sociale", value: "Acme SARL", confidence: 0.94 },
        { key: "effectifs", label: "Effectifs", value: 12, confidence: 0.71 },
      ],
    },
    extraction_validated_at: null,
    extraction_validated_by: null,
    linked_projets: [],
    tags: [],
    deleted_at: null,
    purge_scheduled_at: null,
    ...p,
  }
}

describe("<OcrSummarySheet> (F50)", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("affiche les champs extraits une fois le doc chargé", async () => {
    vi.spyOn(documentsApi, "getDocument").mockResolvedValueOnce(makeDoc())
    const wrapper = mount(OcrSummarySheet, {
      props: { open: true, docId: "doc-1" },
    })
    await flushPromises()
    expect(wrapper.text()).toContain("Raison sociale")
    expect(wrapper.text()).toContain("Effectifs")
    // Confiance affichée (94 % et 71 %).
    expect(wrapper.text()).toContain("94%")
    expect(wrapper.text()).toContain("71%")
  })

  it("affiche le bouton « Répondre librement » (P10)", async () => {
    vi.spyOn(documentsApi, "getDocument").mockResolvedValueOnce(makeDoc())
    const wrapper = mount(OcrSummarySheet, {
      props: { open: true, docId: "doc-1" },
    })
    await flushPromises()
    const btn = wrapper.findAll("button").find((b) => b.text() === "Répondre librement")
    expect(btn).toBeDefined()
    await btn!.trigger("click")
    expect(wrapper.emitted("free-response")).toBeTruthy()
  })

  it("appelle store.validateExtraction avec les valeurs éditées", async () => {
    vi.spyOn(documentsApi, "getDocument").mockResolvedValueOnce(makeDoc())
    const validateSpy = vi
      .spyOn(useDocumentsStore(), "validateExtraction")
      .mockResolvedValue(undefined)
    const wrapper = mount(OcrSummarySheet, {
      props: { open: true, docId: "doc-1" },
    })
    await flushPromises()

    // Modifie le champ Effectifs (2nd input).
    const inputs = wrapper.findAll("input[type=text]")
    expect(inputs).toHaveLength(2)
    await inputs[1]!.setValue("18")

    // Click sur Valider.
    const validateBtn = wrapper.findAll("button").find((b) => b.text().includes("Valider"))
    await validateBtn!.trigger("click")
    await flushPromises()

    expect(validateSpy).toHaveBeenCalledTimes(1)
    const [docId, payload] = validateSpy.mock.calls[0]!
    expect(docId).toBe("doc-1")
    expect(payload.fields).toEqual([
      { key: "raison_sociale", value: "Acme SARL" },
      { key: "effectifs", value: "18" },
    ])
    // propagate_to inclut l'entreprise.
    expect(payload.propagate_to).toEqual([{ entity: "entreprise", id: "ent-1" }])

    // Le composant émet close après validation.
    expect(wrapper.emitted("close")).toBeTruthy()
  })

  it("désactive le bouton Valider quand le doc est déjà validé", async () => {
    vi.spyOn(documentsApi, "getDocument").mockResolvedValueOnce(
      makeDoc({ extraction_validated_at: "2026-05-05T11:00:00Z" }),
    )
    const wrapper = mount(OcrSummarySheet, {
      props: { open: true, docId: "doc-1" },
    })
    await flushPromises()
    const validateBtn = wrapper.findAll("button").find((b) => b.text().includes("Valider"))
    expect(validateBtn?.attributes("disabled")).toBeDefined()
    expect(wrapper.text()).toContain("Document déjà validé")
  })

  it("relance demande confirmation et invalide la validation si confirmé (T081)", async () => {
    vi.spyOn(documentsApi, "getDocument").mockResolvedValueOnce(
      makeDoc({ extraction_validated_at: "2026-05-05T11:00:00Z" }),
    )
    const relaunchSpy = vi
      .spyOn(useDocumentsStore(), "relaunchOcr")
      .mockResolvedValue(undefined)

    // Stub window.confirm — accepte.
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true)
    const wrapper = mount(OcrSummarySheet, {
      props: { open: true, docId: "doc-1" },
    })
    await flushPromises()

    const relaunchBtn = wrapper.findAll("button").find((b) => b.text() === "Relancer extraction")
    await relaunchBtn!.trigger("click")
    await flushPromises()

    expect(confirmSpy).toHaveBeenCalledTimes(1)
    expect(relaunchSpy).toHaveBeenCalledWith("doc-1", { invalidateValidation: true })
    expect(wrapper.emitted("close")).toBeTruthy()
  })

  it("relance abandonne si l'utilisateur annule la confirmation", async () => {
    vi.spyOn(documentsApi, "getDocument").mockResolvedValueOnce(
      makeDoc({ extraction_validated_at: "2026-05-05T11:00:00Z" }),
    )
    const relaunchSpy = vi.spyOn(useDocumentsStore(), "relaunchOcr")
    vi.spyOn(window, "confirm").mockReturnValue(false)
    const wrapper = mount(OcrSummarySheet, {
      props: { open: true, docId: "doc-1" },
    })
    await flushPromises()
    await wrapper
      .findAll("button")
      .find((b) => b.text() === "Relancer extraction")!
      .trigger("click")
    expect(relaunchSpy).not.toHaveBeenCalled()
  })

  it("relance NE demande PAS de confirmation si le doc n'est pas validé", async () => {
    vi.spyOn(documentsApi, "getDocument").mockResolvedValueOnce(makeDoc())
    const relaunchSpy = vi
      .spyOn(useDocumentsStore(), "relaunchOcr")
      .mockResolvedValue(undefined)
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true)
    const wrapper = mount(OcrSummarySheet, {
      props: { open: true, docId: "doc-1" },
    })
    await flushPromises()
    await wrapper
      .findAll("button")
      .find((b) => b.text() === "Relancer extraction")!
      .trigger("click")
    await flushPromises()
    expect(confirmSpy).not.toHaveBeenCalled()
    expect(relaunchSpy).toHaveBeenCalledWith("doc-1", { invalidateValidation: false })
  })

  it("affiche un message d'erreur si getDocument échoue", async () => {
    vi.spyOn(documentsApi, "getDocument").mockRejectedValueOnce(new Error("boom"))
    const wrapper = mount(OcrSummarySheet, {
      props: { open: true, docId: "doc-1" },
    })
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.find('[role="alert"]').text()).toContain("boom")
  })

  it("ne rend pas la dialog quand open=false", () => {
    const wrapper = mount(OcrSummarySheet, {
      props: { open: false, docId: "doc-1" },
    })
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it("close émis quand on clique sur le bouton ✕", async () => {
    vi.spyOn(documentsApi, "getDocument").mockResolvedValueOnce(makeDoc())
    const wrapper = mount(OcrSummarySheet, {
      props: { open: true, docId: "doc-1" },
    })
    await flushPromises()
    const closeBtn = wrapper.findAll("button").find((b) => b.attributes("aria-label") === "Fermer")
    await closeBtn!.trigger("click")
    expect(wrapper.emitted("close")).toBeTruthy()
  })
})
