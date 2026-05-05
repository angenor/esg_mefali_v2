// F43 T027 — tests CountryMultiSelect : ordre UEMOA/CEDEAO, recherche, refus hors-liste.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import CountryMultiSelect from "~/components/profil/CountryMultiSelect.vue"

describe("CountryMultiSelect", () => {
  it("rend les chips pour les codes ISO2 fournis", () => {
    const wrapper = mount(CountryMultiSelect, {
      props: { modelValue: ["BJ", "CI"] },
    })
    expect(wrapper.text()).toContain("Bénin")
    expect(wrapper.text()).toContain("Côte d'Ivoire")
  })

  it("ouvre la liste au focus et affiche UEMOA en premier", async () => {
    const wrapper = mount(CountryMultiSelect, { props: { modelValue: [] } })
    await wrapper.find("input").trigger("focus")
    const items = wrapper.findAll('[role="option"]')
    expect(items.length).toBeGreaterThan(0)
    // Le premier item visible doit être un UEMOA (BJ ou similaire).
    expect(items[0]!.attributes("data-cluster")).toBe("uemoa")
  })

  it("recherche par nom (« sén » → Sénégal)", async () => {
    const wrapper = mount(CountryMultiSelect, { props: { modelValue: [] } })
    await wrapper.find("input").trigger("focus")
    await wrapper.find("input").setValue("sén")
    const items = wrapper.findAll('[role="option"]')
    expect(items.some((i) => i.text().includes("Sénégal"))).toBe(true)
  })

  it("recherche par code ISO (« ci » → Côte d'Ivoire)", async () => {
    const wrapper = mount(CountryMultiSelect, { props: { modelValue: [] } })
    await wrapper.find("input").trigger("focus")
    await wrapper.find("input").setValue("ci")
    const items = wrapper.findAll('[role="option"]')
    expect(items.some((i) => i.text().includes("Côte d'Ivoire"))).toBe(true)
  })

  it("clic sur option ajoute le code et emit update:modelValue", async () => {
    const wrapper = mount(CountryMultiSelect, { props: { modelValue: [] } })
    await wrapper.find("input").trigger("focus")
    const first = wrapper.find('[role="option"]')
    await first.trigger("mousedown")
    const events = wrapper.emitted("update:modelValue")
    expect(events).toBeTruthy()
    expect((events![0]?.[0] as string[]).length).toBe(1)
  })

  it("retire un chip via le bouton ×", async () => {
    const wrapper = mount(CountryMultiSelect, { props: { modelValue: ["BJ"] } })
    await wrapper.find(".country-multi__remove").trigger("click")
    const events = wrapper.emitted("update:modelValue")
    expect(events).toBeTruthy()
    expect(events![0]?.[0]).toEqual([])
  })

  it("mode mono : nouvelle sélection remplace l'existante", async () => {
    const wrapper = mount(CountryMultiSelect, {
      props: { modelValue: ["BJ"], mono: true },
    })
    await wrapper.find("input").trigger("focus")
    await wrapper.find("input").setValue("Sénégal")
    const items = wrapper.findAll('[role="option"]')
    await items[0]!.trigger("mousedown")
    const events = wrapper.emitted("update:modelValue")
    const last = events![events!.length - 1]?.[0] as string[]
    expect(last.length).toBe(1)
    expect(last[0]).not.toBe("BJ")
  })

  it("max appliqué : ignore l'ajout si seuil atteint", async () => {
    const wrapper = mount(CountryMultiSelect, {
      props: { modelValue: ["BJ", "CI"], max: 2 },
    })
    await wrapper.find("input").trigger("focus")
    const items = wrapper.findAll('[role="option"]')
    await items[0]!.trigger("mousedown")
    expect(wrapper.emitted("update:modelValue")).toBeFalsy()
  })

  it("backspace efface la dernière chip quand input vide", async () => {
    const wrapper = mount(CountryMultiSelect, { props: { modelValue: ["BJ", "CI"] } })
    const input = wrapper.find("input")
    await input.trigger("focus")
    await input.trigger("keydown", { key: "Backspace" })
    const events = wrapper.emitted("update:modelValue")
    expect(events).toBeTruthy()
    expect(events![0]?.[0]).toEqual(["BJ"])
  })
})
