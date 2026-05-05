// F50 (T068) — Tests DeleteConfirmModal.

import { describe, expect, it } from "vitest"
import { flushPromises, mount } from "@vue/test-utils"

import DeleteConfirmModal from "../../app/components/documents/DeleteConfirmModal.vue"

describe("<DeleteConfirmModal> (F50)", () => {
  it("ne rend rien tant que open=false", () => {
    const wrapper = mount(DeleteConfirmModal, {
      props: { open: false, documentName: "x.pdf" },
    })
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it("rend une dialog ARIA et affiche le nom du document", () => {
    const wrapper = mount(DeleteConfirmModal, {
      props: { open: true, documentName: "Statuts.pdf" },
    })
    const dlg = wrapper.find('[role="dialog"]')
    expect(dlg.exists()).toBe(true)
    expect(dlg.attributes("aria-modal")).toBe("true")
    expect(dlg.attributes("aria-labelledby")).toBe("delete-modal-title")
    expect(wrapper.text()).toContain("Statuts.pdf")
    expect(wrapper.text()).toContain("30 jours")
  })

  it("émet cancel au clic sur Annuler", async () => {
    const wrapper = mount(DeleteConfirmModal, {
      props: { open: true, documentName: "x.pdf" },
    })
    const cancelBtn = wrapper.findAll("button").find((b) => b.text() === "Annuler")
    await cancelBtn!.trigger("click")
    expect(wrapper.emitted("cancel")).toBeTruthy()
  })

  it("émet confirm au clic sur Supprimer", async () => {
    const wrapper = mount(DeleteConfirmModal, {
      props: { open: true, documentName: "x.pdf" },
    })
    const supBtn = wrapper.findAll("button").find((b) => b.text() === "Supprimer")
    await supBtn!.trigger("click")
    expect(wrapper.emitted("confirm")).toBeTruthy()
  })

  it("Escape émet cancel quand open=true", async () => {
    const wrapper = mount(DeleteConfirmModal, {
      props: { open: true, documentName: "x.pdf" },
    })
    await wrapper.find('[role="dialog"]').trigger("keydown", { key: "Escape" })
    expect(wrapper.emitted("cancel")).toBeTruthy()
  })

  it("focus le bouton Annuler à l'ouverture", async () => {
    const wrapper = mount(DeleteConfirmModal, {
      props: { open: false, documentName: "x.pdf" },
      attachTo: document.body,
    })
    await wrapper.setProps({ open: true })
    await flushPromises()
    // Le focus va sur le bouton "Annuler" via cancelBtn ref.
    const cancelBtn = wrapper.findAll("button").find((b) => b.text() === "Annuler")
    expect(document.activeElement).toBe(cancelBtn!.element)
    wrapper.unmount()
  })
})
