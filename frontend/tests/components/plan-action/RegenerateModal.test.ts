// F45 T041 — Tests RegenerateModal.
import { describe, expect, it, vi, beforeEach } from "vitest"
import { mount, flushPromises } from "@vue/test-utils"
import RegenerateModal from "~/components/plan-action/RegenerateModal.vue"

vi.mock("gsap", () => ({ gsap: { fromTo: vi.fn() }, default: { fromTo: vi.fn() } }))

beforeEach(() => {
  document.body.innerHTML = ""
})

describe("RegenerateModal", () => {
  it("open=true → modale rendue avec rôle dialog + aria-modal", async () => {
    mount(RegenerateModal, { props: { open: true, defaultHorizon: 12, busy: false } })
    await flushPromises()
    const dialog = document.querySelector('[role="dialog"]')
    expect(dialog).not.toBeNull()
    expect(dialog?.getAttribute("aria-modal")).toBe("true")
  })

  it("open=false → modale absente du DOM", async () => {
    mount(RegenerateModal, { props: { open: false, defaultHorizon: 12, busy: false } })
    await flushPromises()
    expect(document.querySelector('[role="dialog"]')).toBeNull()
  })

  it("trois radios horizon (6 / 12 / 24) avec defaultHorizon présélectionné", async () => {
    mount(RegenerateModal, { props: { open: true, defaultHorizon: 12, busy: false } })
    await flushPromises()
    const radios = document.querySelectorAll(
      'input[type="radio"][name="pa-regen-horizon"]',
    ) as NodeListOf<HTMLInputElement>
    expect(radios.length).toBe(3)
    const checked = Array.from(radios).find((r) => r.checked)
    expect(checked?.value).toBe("12")
  })

  it("clic sur Confirmer émet confirm avec horizon courant", async () => {
    const w = mount(RegenerateModal, {
      props: { open: true, defaultHorizon: 6, busy: false },
    })
    await flushPromises()
    const confirmBtn = document.querySelector(".pa-regen__confirm") as HTMLButtonElement
    confirmBtn.click()
    expect(w.emitted("confirm")?.[0]).toEqual([6])
  })

  it("changement de radio puis confirm → confirm avec nouvelle valeur", async () => {
    const w = mount(RegenerateModal, {
      props: { open: true, defaultHorizon: 12, busy: false },
    })
    await flushPromises()
    const radio24 = Array.from(
      document.querySelectorAll('input[type="radio"][name="pa-regen-horizon"]'),
    ).find((r) => (r as HTMLInputElement).value === "24") as HTMLInputElement
    radio24.checked = true
    radio24.dispatchEvent(new Event("change"))
    await flushPromises()
    const confirmBtn = document.querySelector(".pa-regen__confirm") as HTMLButtonElement
    confirmBtn.click()
    expect(w.emitted("confirm")?.[0]).toEqual([24])
  })

  it("busy=true → bouton confirm disabled (pas d'émission)", async () => {
    const w = mount(RegenerateModal, {
      props: { open: true, defaultHorizon: 12, busy: true },
    })
    await flushPromises()
    const confirmBtn = document.querySelector(".pa-regen__confirm") as HTMLButtonElement
    expect(confirmBtn.disabled).toBe(true)
    confirmBtn.click()
    expect(w.emitted("confirm")).toBeUndefined()
  })

  it("clic sur Annuler émet cancel", async () => {
    const w = mount(RegenerateModal, {
      props: { open: true, defaultHorizon: 12, busy: false },
    })
    await flushPromises()
    const cancelBtn = document.querySelector(".pa-regen__cancel") as HTMLButtonElement
    cancelBtn.click()
    expect(w.emitted("cancel")?.length).toBeGreaterThan(0)
  })
})
