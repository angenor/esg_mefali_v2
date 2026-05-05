// F50 (T019) — Tests UploadZone : drag & drop, validation MIME/20Mo, queue,
// événement duplicate-detected, parcours clavier (FR-A11Y-003).

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { mount, flushPromises } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"

// $fetch + apiBase pour le service documentsApi.
const fetchMock = vi.fn()
;(globalThis as { $fetch?: unknown }).$fetch = fetchMock
;(globalThis as { useRuntimeConfig?: unknown }).useRuntimeConfig = () => ({
  public: { apiBase: "http://api" },
})

// Stub crypto.subtle.digest sans casser le getter happy-dom.
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
} else {
  Object.defineProperty(
    (globalThis.crypto as Crypto).subtle ?? (globalThis.crypto as unknown as { subtle: object }),
    "digest",
    { configurable: true, value: fakeDigest },
  )
}

// Stub BroadcastChannel (Pinia + structuredClone incompat).
class FakeBC {
  postMessage(): void {}
  addEventListener(): void {}
  removeEventListener(): void {}
  close(): void {}
}
;(globalThis as { BroadcastChannel?: unknown }).BroadcastChannel =
  FakeBC as unknown as typeof BroadcastChannel

import UploadZone from "../../app/components/documents/UploadZone.vue"
import { documentsApi } from "../../app/services/api/documents"
import { useDocumentsStore } from "../../app/stores/documents"

function pdfFile(size = 1024, name = "doc.pdf"): File {
  return new File([new Uint8Array(size)], name, { type: "application/pdf" })
}

describe("<UploadZone> (F50)", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it("rend la zone de dépôt avec ARIA appropriée", () => {
    const wrapper = mount(UploadZone, { props: { context: "entreprise" } })
    const zone = wrapper.find('[role="button"]')
    expect(zone.exists()).toBe(true)
    expect(zone.attributes("tabindex")).toBe("0")
    expect(zone.attributes("aria-label")).toContain("Zone de dépôt")
    expect(wrapper.text()).toContain("PDF, JPG, PNG, DOCX, XLSX")
  })

  it("Enter et Espace ouvrent le picker (parcours clavier FR-A11Y-003)", async () => {
    const wrapper = mount(UploadZone, { props: { context: "entreprise" } })
    const input = wrapper.find("input[type=file]").element as HTMLInputElement
    const clickSpy = vi.spyOn(input, "click").mockImplementation(() => undefined)
    await wrapper.find('[role="button"]').trigger("keydown", { key: "Enter" })
    expect(clickSpy).toHaveBeenCalledTimes(1)
    await wrapper.find('[role="button"]').trigger("keydown", { key: " " })
    expect(clickSpy).toHaveBeenCalledTimes(2)
  })

  it("rejette un MIME hors whitelist avec un message d'erreur visible", async () => {
    const wrapper = mount(UploadZone, { props: { context: "entreprise" } })
    const enqueueSpy = vi.spyOn(useDocumentsStore(), "enqueueUpload")

    const evilFile = new File(["x"], "evil.exe", { type: "application/x-msdownload" })
    const dataTransfer = { files: [evilFile] } as unknown as DataTransfer

    await wrapper.find('[role="button"]').trigger("drop", { dataTransfer })
    await flushPromises()

    expect(enqueueSpy).not.toHaveBeenCalled()
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.find('[role="alert"]').text()).toContain("evil.exe")
  })

  it("rejette un fichier > 20 Mo (cap UI strict FR-002)", async () => {
    const wrapper = mount(UploadZone, { props: { context: "entreprise" } })
    const enqueueSpy = vi.spyOn(useDocumentsStore(), "enqueueUpload")
    const big = pdfFile(21 * 1024 * 1024, "big.pdf")
    const dataTransfer = { files: [big] } as unknown as DataTransfer

    await wrapper.find('[role="button"]').trigger("drop", { dataTransfer })
    await flushPromises()

    expect(enqueueSpy).not.toHaveBeenCalled()
    expect(wrapper.find('[role="alert"]').text()).toContain("trop volumineux")
  })

  it("accepte un PDF valide et appelle store.enqueueUpload", async () => {
    const wrapper = mount(UploadZone, {
      props: { context: "entreprise", docType: "statuts" },
    })
    const enqueueSpy = vi
      .spyOn(useDocumentsStore(), "enqueueUpload")
      .mockResolvedValue({
        id: "job1",
        file: pdfFile(),
        filename: "doc.pdf",
        size: 1024,
        mime: "application/pdf",
        sha256: null,
        percent: 0,
        status: "pending",
      })
    const file = pdfFile(1024, "doc.pdf")
    const dataTransfer = { files: [file] } as unknown as DataTransfer

    await wrapper.find('[role="button"]').trigger("drop", { dataTransfer })
    await flushPromises()

    expect(enqueueSpy).toHaveBeenCalledWith(
      expect.any(File),
      expect.objectContaining({ type: "statuts" }),
    )
  })

  it("propage linkProjetId quand le composant est monté en contexte projet", async () => {
    const wrapper = mount(UploadZone, {
      props: { context: "projet", projetId: "p-uuid", docType: "facture" },
    })
    const enqueueSpy = vi
      .spyOn(useDocumentsStore(), "enqueueUpload")
      .mockResolvedValue({
        id: "j",
        file: pdfFile(),
        filename: "f.pdf",
        size: 100,
        mime: "application/pdf",
        sha256: null,
        percent: 0,
        status: "pending",
      })
    await wrapper.find('[role="button"]').trigger("drop", {
      dataTransfer: { files: [pdfFile()] } as unknown as DataTransfer,
    })
    await flushPromises()
    expect(enqueueSpy).toHaveBeenCalledWith(
      expect.any(File),
      expect.objectContaining({ linkProjetId: "p-uuid", type: "facture" }),
    )
  })

  it("émet duplicate-detected quand le store passe le job en duplicate", async () => {
    vi.useFakeTimers()
    const store = useDocumentsStore()
    // Stub enqueueUpload pour insérer manuellement un job en queue.
    vi.spyOn(store, "enqueueUpload").mockImplementation(async (file) => {
      const job = {
        id: "job-dup",
        file,
        filename: file.name,
        size: file.size,
        mime: file.type,
        sha256: "abc123",
        percent: 0,
        status: "pending" as const,
      }
      store.uploadQueue = [...store.uploadQueue, job]
      // Marque duplicate après le rendu (latence simulée).
      setTimeout(() => {
        store.uploadQueue = store.uploadQueue.map((j) =>
          j.id === "job-dup" ? { ...j, status: "duplicate", sha256: "abc123" } : j,
        )
      }, 200)
      return job
    })

    const wrapper = mount(UploadZone, { props: { context: "entreprise" } })
    await wrapper.find('[role="button"]').trigger("drop", {
      dataTransfer: { files: [pdfFile()] } as unknown as DataTransfer,
    })
    await flushPromises()

    // Avance les timers internes (watchJobForDuplicate poll 100 ms).
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()

    const events = wrapper.emitted("duplicate-detected")
    expect(events).toBeTruthy()
    expect(events?.[0]?.[0]).toMatchObject({
      jobId: "job-dup",
      existingId: "abc123",
    })
  })

  it("dragOver active la classe visuelle, dragLeave la retire", async () => {
    const wrapper = mount(UploadZone, { props: { context: "entreprise" } })
    const zone = wrapper.find('[role="button"]')
    await zone.trigger("dragover")
    expect(zone.classes().some((c) => c.includes("emerald-500"))).toBe(true)
    await zone.trigger("dragleave")
    expect(zone.classes().some((c) => c.includes("emerald-500"))).toBe(false)
  })
})
