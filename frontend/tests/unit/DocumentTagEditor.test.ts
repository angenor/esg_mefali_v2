// F50 (T059) — Tests DocumentTagEditor.

import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"

import DocumentTagEditor from "../../app/components/documents/DocumentTagEditor.vue"

describe("<DocumentTagEditor> (F50)", () => {
  it("rend les tags actuels comme chips", () => {
    const wrapper = mount(DocumentTagEditor, {
      props: { modelValue: ["Bilan", "Statuts"], documentId: "d1" },
    })
    expect(wrapper.text()).toContain("Bilan")
    expect(wrapper.text()).toContain("Statuts")
    // Chaque chip a un bouton de retrait avec aria-label dédié.
    expect(
      wrapper
        .findAll("button")
        .find((b) => b.attributes("aria-label") === "Retirer le tag Bilan"),
    ).toBeDefined()
  })

  it("ajoute un tag à Enter et émet update:modelValue + commit", async () => {
    const wrapper = mount(DocumentTagEditor, {
      props: { modelValue: ["A"], documentId: "d1" },
    })
    const input = wrapper.find("input")
    await input.setValue("Nouveau")
    await input.trigger("keydown", { key: "Enter" })
    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([["A", "Nouveau"]])
    expect(wrapper.emitted("commit")?.[0]).toEqual([
      { id: "d1", tags: ["A", "Nouveau"] },
    ])
  })

  it("ajoute aussi à la virgule", async () => {
    const wrapper = mount(DocumentTagEditor, {
      props: { modelValue: [], documentId: "d1" },
    })
    const input = wrapper.find("input")
    await input.setValue("X")
    await input.trigger("keydown", { key: "," })
    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([["X"]])
  })

  it("refuse un tag vide après trim", async () => {
    const wrapper = mount(DocumentTagEditor, {
      props: { modelValue: [], documentId: "d1" },
    })
    const input = wrapper.find("input")
    await input.setValue("   ")
    await input.trigger("keydown", { key: "Enter" })
    expect(wrapper.emitted("update:modelValue")).toBeFalsy()
  })

  it("refuse un tag dépassant maxLength", async () => {
    const wrapper = mount(DocumentTagEditor, {
      props: { modelValue: [], documentId: "d1", maxLength: 5 },
    })
    const input = wrapper.find("input")
    await input.setValue("trop long")
    await input.trigger("keydown", { key: "Enter" })
    expect(wrapper.emitted("update:modelValue")).toBeFalsy()
  })

  it("retire un tag au clic sur ×", async () => {
    const wrapper = mount(DocumentTagEditor, {
      props: { modelValue: ["A", "B"], documentId: "d1" },
    })
    const removeA = wrapper
      .findAll("button")
      .find((b) => b.attributes("aria-label") === "Retirer le tag A")
    await removeA!.trigger("click")
    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([["B"]])
    expect(wrapper.emitted("commit")?.[0]).toEqual([{ id: "d1", tags: ["B"] }])
  })

  it("Backspace en input vide retire le dernier tag", async () => {
    const wrapper = mount(DocumentTagEditor, {
      props: { modelValue: ["A", "B"], documentId: "d1" },
    })
    const input = wrapper.find("input")
    await input.trigger("keydown", { key: "Backspace" })
    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([["A"]])
  })

  it("ne dédoublonne pas (tag déjà présent → no-op)", async () => {
    const wrapper = mount(DocumentTagEditor, {
      props: { modelValue: ["A"], documentId: "d1" },
    })
    const input = wrapper.find("input")
    await input.setValue("A")
    await input.trigger("keydown", { key: "Enter" })
    expect(wrapper.emitted("update:modelValue")).toBeFalsy()
    // Le draft doit être vidé après tentative.
    expect((input.element as HTMLInputElement).value).toBe("")
  })

  it("ajoute aussi sur blur", async () => {
    const wrapper = mount(DocumentTagEditor, {
      props: { modelValue: [], documentId: "d1" },
    })
    const input = wrapper.find("input")
    await input.setValue("OnBlur")
    await input.trigger("blur")
    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([["OnBlur"]])
  })
})
