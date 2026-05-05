// F45 T047 — Tests HorizonToggle.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import HorizonToggle from "~/components/plan-action/HorizonToggle.vue"

describe("HorizonToggle", () => {
  it("rend trois boutons (6 / 12 / 24)", () => {
    const w = mount(HorizonToggle, { props: { modelValue: 12 } })
    const btns = w.findAll(".pa-horizon__btn")
    expect(btns).toHaveLength(3)
  })

  it("modelValue=12 → bouton 12 actif (aria-pressed=true)", () => {
    const w = mount(HorizonToggle, { props: { modelValue: 12 } })
    const btns = w.findAll(".pa-horizon__btn")
    const active = btns.find((b) => b.attributes("aria-pressed") === "true")
    expect(active?.text()).toContain("12")
  })

  it("clic sur bouton émet update:modelValue avec la valeur", async () => {
    const w = mount(HorizonToggle, { props: { modelValue: 12 } })
    const btns = w.findAll(".pa-horizon__btn")
    await btns[2]!.trigger("click")
    expect(w.emitted("update:modelValue")?.[0]).toEqual([24])
  })

  it("clic sur le bouton actif n'émet rien", async () => {
    const w = mount(HorizonToggle, { props: { modelValue: 12 } })
    const active = w.findAll(".pa-horizon__btn").find((b) => b.attributes("aria-pressed") === "true")!
    await active.trigger("click")
    expect(w.emitted("update:modelValue")).toBeUndefined()
  })

  it("a11y : role=tablist sur le conteneur", () => {
    const w = mount(HorizonToggle, { props: { modelValue: 6 } })
    expect(w.find('[role="tablist"]').exists()).toBe(true)
  })
})
