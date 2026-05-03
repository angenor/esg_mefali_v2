// F43 T056 — tests ProjetDocuments : upload OK, MIME refusé, taille refusée.
import { beforeEach, describe, expect, it, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { setActivePinia, createPinia } from "pinia"
import ProjetDocuments from "~/components/profil/ProjetDocuments.vue"
import { useProjetsStore } from "~/stores/projets"

vi.stubGlobal(
  "useRuntimeConfig",
  () => ({ public: { apiBase: "http://localhost:8010" } }),
)

function makeFile(name: string, type: string, size: number): File {
  const f = new File([new Uint8Array(size)], name, { type })
  Object.defineProperty(f, "size", { value: size })
  return f
}

describe("ProjetDocuments", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it("rend la liste empty si aucun document", () => {
    const wrapper = mount(ProjetDocuments, { props: { projetId: "p1" } })
    expect(wrapper.text()).toContain("Aucun document")
  })

  it("rend la liste des documents existants", () => {
    const store = useProjetsStore()
    store.documentsById = {
      p1: [
        {
          id: "d1",
          projet_id: "p1",
          nom: "rapport.pdf",
          mime: "application/pdf",
          taille_octets: 2048,
          type_doc: "autre",
          created_at: new Date().toISOString(),
        },
      ],
    }
    const wrapper = mount(ProjetDocuments, { props: { projetId: "p1" } })
    expect(wrapper.text()).toContain("rapport.pdf")
  })

  it("refuse un MIME hors whitelist (.txt)", async () => {
    const $fetchMock = vi.fn()
    vi.stubGlobal("$fetch", $fetchMock)
    const wrapper = mount(ProjetDocuments, { props: { projetId: "p1" } })
    const file = makeFile("note.txt", "text/plain", 100)
    const input = wrapper.find("input[type=file]")
    Object.defineProperty(input.element, "files", { value: [file], configurable: true })
    await input.trigger("change")
    expect($fetchMock).not.toHaveBeenCalled()
  })

  it("refuse un fichier > 25 Mo", async () => {
    const $fetchMock = vi.fn()
    vi.stubGlobal("$fetch", $fetchMock)
    const wrapper = mount(ProjetDocuments, { props: { projetId: "p1" } })
    const file = makeFile("gros.pdf", "application/pdf", 26 * 1024 * 1024)
    const input = wrapper.find("input[type=file]")
    Object.defineProperty(input.element, "files", { value: [file], configurable: true })
    await input.trigger("change")
    expect($fetchMock).not.toHaveBeenCalled()
  })

  it("upload OK : PDF de taille valide → POST appelé", async () => {
    const $fetchMock = vi.fn().mockResolvedValue({
      id: "d2",
      projet_id: "p1",
      nom: "ok.pdf",
      mime: "application/pdf",
      taille_octets: 1000,
      type_doc: "autre",
      created_at: new Date().toISOString(),
    })
    vi.stubGlobal("$fetch", $fetchMock)
    const wrapper = mount(ProjetDocuments, { props: { projetId: "p1" } })
    const file = makeFile("ok.pdf", "application/pdf", 1000)
    const input = wrapper.find("input[type=file]")
    Object.defineProperty(input.element, "files", { value: [file], configurable: true })
    await input.trigger("change")
    expect($fetchMock).toHaveBeenCalled()
  })
})
