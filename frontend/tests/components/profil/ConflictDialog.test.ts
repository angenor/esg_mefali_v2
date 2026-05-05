// F43 T008 — tests ConflictDialog (props/emits, role alertdialog, focus initial).
import { describe, expect, it, vi } from "vitest"
import { mount } from "@vue/test-utils"
import ConflictDialog from "~/components/profil/ConflictDialog.vue"

// Mock gsap pour éviter de toucher au DOM en test.
vi.mock("gsap", () => ({ gsap: { fromTo: vi.fn() } }))

describe("ConflictDialog", () => {
  it("ne rend rien quand open=false", () => {
    const wrapper = mount(ConflictDialog, {
      props: { open: false, field: "raison_sociale", yourValue: "A", currentValue: "B" },
      attachTo: document.body,
    })
    expect(document.querySelector('[role="alertdialog"]')).toBeNull()
    wrapper.unmount()
  })

  it("rend role=alertdialog avec aria-labelledby quand open=true", async () => {
    const wrapper = mount(ConflictDialog, {
      props: { open: true, field: "raison_sociale", yourValue: "A", currentValue: "B" },
      attachTo: document.body,
    })
    const dialog = document.querySelector('[role="alertdialog"]')
    expect(dialog).not.toBeNull()
    expect(dialog?.getAttribute("aria-labelledby")).toBe("conflict-dialog-title")
    wrapper.unmount()
  })

  it("affiche les deux valeurs (mine/theirs)", () => {
    const wrapper = mount(ConflictDialog, {
      props: {
        open: true,
        field: "raison_sociale",
        yourValue: "ACME SARL",
        currentValue: "ACME SA",
      },
      attachTo: document.body,
    })
    const text = document.body.textContent ?? ""
    expect(text).toContain("ACME SARL")
    expect(text).toContain("ACME SA")
    wrapper.unmount()
  })

  it("émet resolve('mine') au clic sur 'Garder ma valeur'", async () => {
    const wrapper = mount(ConflictDialog, {
      props: { open: true, field: "raison_sociale", yourValue: "A", currentValue: "B" },
      attachTo: document.body,
    })
    const btn = document.body.querySelector(".conflict-dialog__btn--primary") as HTMLButtonElement
    btn.click()
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted("resolve")?.[0]).toEqual(["mine"])
    wrapper.unmount()
  })

  it("émet resolve('theirs') puis resolve('cancel')", async () => {
    const wrapper = mount(ConflictDialog, {
      props: { open: true, field: "raison_sociale", yourValue: "A", currentValue: "B" },
      attachTo: document.body,
    })
    const buttons = document.body.querySelectorAll(".conflict-dialog__btn")
    ;(buttons[1] as HTMLButtonElement).click()
    ;(buttons[2] as HTMLButtonElement).click()
    await wrapper.vm.$nextTick()
    const events = wrapper.emitted("resolve") ?? []
    expect(events[0]).toEqual(["theirs"])
    expect(events[1]).toEqual(["cancel"])
    wrapper.unmount()
  })

  it("affiche le label FR du champ si fourni", () => {
    const wrapper = mount(ConflictDialog, {
      props: {
        open: true,
        field: "raison_sociale",
        fieldLabel: "Raison sociale",
        yourValue: "A",
        currentValue: "B",
      },
      attachTo: document.body,
    })
    expect(document.body.textContent).toContain("Raison sociale")
    wrapper.unmount()
  })
})
