// F43 T026 — tests MoneyField : Decimal in/out, devise XOF/EUR/USD, conversion live (P5).
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import MoneyField from "~/components/profil/MoneyField.vue"

describe("MoneyField", () => {
  it("rend la valeur initiale en mode XOF avec affichage parallèle EUR", () => {
    const wrapper = mount(MoneyField, {
      props: { modelValue: { amount: "1250000", currency: "XOF" }, label: "CA" },
    })
    const display = wrapper.find('[data-testid="money-display"]')
    expect(display.exists()).toBe(true)
    expect(display.text()).toContain("FCFA")
    expect(display.text()).toContain("≈")
    expect(display.text()).toContain("€")
  })

  it("emit modelValue avec amount toujours en string (jamais Number)", async () => {
    const wrapper = mount(MoneyField, {
      props: { modelValue: null, label: "CA" },
    })
    await wrapper.find("input").setValue("50000000")
    const events = wrapper.emitted("update:modelValue")
    expect(events).toBeTruthy()
    const last = events![events!.length - 1]?.[0] as { amount: string; currency: string } | null
    expect(last).toEqual({ amount: "50000000", currency: "XOF" })
    expect(typeof last!.amount).toBe("string")
  })

  it("change la devise → emit nouvelle currency", async () => {
    const wrapper = mount(MoneyField, {
      props: { modelValue: { amount: "100", currency: "XOF" }, label: "CA" },
    })
    await wrapper.find("select").setValue("EUR")
    const events = wrapper.emitted("update:modelValue")
    const last = events![events!.length - 1]?.[0] as { amount: string; currency: string }
    expect(last.currency).toBe("EUR")
    expect(typeof last.amount).toBe("string")
  })

  it("USD : pas de conversion live (R7) — affiche '≈ –'", () => {
    const wrapper = mount(MoneyField, {
      props: { modelValue: { amount: "1000", currency: "USD" }, label: "CA" },
    })
    const display = wrapper.find('[data-testid="money-display"]')
    expect(display.text()).toContain("$")
    expect(display.text()).toContain("≈ –")
  })

  it("convertit 50_000_000 XOF → ≈ 76 224,51 € (peg 655.957)", () => {
    const wrapper = mount(MoneyField, {
      props: { modelValue: { amount: "50000000", currency: "XOF" } },
    })
    const display = wrapper.find('[data-testid="money-display"]')
    expect(display.text()).toMatch(/76\s?224,51 €/)
  })

  it("efface l'input → emit null", async () => {
    const wrapper = mount(MoneyField, {
      props: { modelValue: { amount: "100", currency: "XOF" } },
    })
    await wrapper.find("input").setValue("")
    const events = wrapper.emitted("update:modelValue")
    const last = events![events!.length - 1]?.[0]
    expect(last).toBeNull()
  })

  it("input invalide ('abc') : pas d'emit", async () => {
    const wrapper = mount(MoneyField, {
      props: { modelValue: null },
    })
    await wrapper.find("input").setValue("abc")
    expect(wrapper.emitted("update:modelValue")).toBeFalsy()
  })

  it("affiche un message d'erreur quand prop error est fournie", () => {
    const wrapper = mount(MoneyField, {
      props: { modelValue: null, error: "Montant requis" },
    })
    expect(wrapper.text()).toContain("Montant requis")
    expect(wrapper.attributes("data-error")).toBeDefined()
  })
})
