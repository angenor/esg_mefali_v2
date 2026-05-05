// F49 T034 — Tests composant GenerateReportModal.

import { beforeEach, describe, expect, it, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"

const fetchMock = vi.fn()
;(globalThis as { $fetch?: unknown }).$fetch = fetchMock
;(globalThis as { useRuntimeConfig?: unknown }).useRuntimeConfig = () => ({
  public: { apiBase: "http://api" },
})

import GenerateReportModal from "../../app/components/rapports/GenerateReportModal.vue"
import { useEntrepriseStore } from "../../app/stores/entreprise"

const entityId = "22222222-2222-2222-2222-222222222222"
const fakeRow = {
  rapport_id: "11111111-1111-1111-1111-111111111111",
  entity_type: "entreprise",
  entity_id: entityId,
  referentiels: ["ESG_MEFALI"],
  language: "fr",
  file_size_bytes: 1234,
  generated_at: "2026-05-04T10:30:00Z",
  download_url: "/me/rapports/.../download",
}

describe("<GenerateReportModal>", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchMock.mockReset()
  })

  function $(sel: string): HTMLElement | null {
    return document.body.querySelector(sel) as HTMLElement | null
  }

  it("ne s'affiche pas si open=false", () => {
    const w = mount(GenerateReportModal, { props: { open: false } })
    expect($('[data-testid="generate-modal"]')).toBeNull()
    w.unmount()
  })

  it("affiche le formulaire avec les champs requis si open=true", async () => {
    const w = mount(GenerateReportModal, { props: { open: true } })
    await w.vm.$nextTick()
    expect($('[data-testid="select-type"]')).not.toBeNull()
    expect($('[data-testid="select-ref"]')).not.toBeNull()
    expect($('[data-testid="input-from"]')).not.toBeNull()
    expect($('[data-testid="input-to"]')).not.toBeNull()
    expect($('[data-testid="submit-btn"]')).not.toBeNull()
    w.unmount()
  })

  it("submit invalide est ignoré (bouton désactivé)", async () => {
    const w = mount(GenerateReportModal, { props: { open: true } })
    await w.vm.$nextTick()
    const from = $('[data-testid="input-from"]') as HTMLInputElement
    from.value = ""
    from.dispatchEvent(new Event("input"))
    await w.vm.$nextTick()
    const btn = $('[data-testid="submit-btn"]') as HTMLButtonElement
    expect(btn.disabled).toBe(true)
    w.unmount()
  })

  it("affiche un message d'erreur si le profil entreprise est indisponible", async () => {
    void useEntrepriseStore() // initialise le store
    const w = mount(GenerateReportModal, { props: { open: true } })
    await w.vm.$nextTick()
    const form = $('[data-testid="submit-btn"]')?.closest("form") as HTMLFormElement
    form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }))
    await new Promise((r) => setTimeout(r, 5))
    await w.vm.$nextTick()
    expect($('[data-testid="error-msg"]')?.textContent).toContain("Profil")
    w.unmount()
  })

  it("preremplit les champs depuis prefill", async () => {
    void useEntrepriseStore()
    const w = mount(GenerateReportModal, {
      props: {
        open: true,
        prefill: {
          type: "carbone",
          referentiel_id: "BOAD",
          period_from: "2024-01-01",
          period_to: "2024-12-31",
        },
      },
    })
    await w.vm.$nextTick()
    const t = $('[data-testid="select-type"]') as HTMLSelectElement
    expect(t.value).toBe("carbone")
    const ref = $('[data-testid="select-ref"]') as HTMLSelectElement
    expect(ref.value).toBe("BOAD")
    w.unmount()
  })
})
