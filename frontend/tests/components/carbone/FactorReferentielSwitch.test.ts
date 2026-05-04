// F47 T084 [US8] — Tests FactorReferentielSwitch.
import { describe, expect, it, vi } from "vitest"
import { mount } from "@vue/test-utils"
import FactorReferentielSwitch from "~/components/carbone/FactorReferentielSwitch.vue"

vi.mock("~/composables/useT", () => ({
  useT: () => ({ t: (k: string) => k }),
}))

vi.mock("~/composables/useReducedMotion", () => ({
  useReducedMotion: () => ({ value: false }),
}))

vi.mock("~/composables/useFloating", () => ({
  useFloating: () => ({
    referenceRef: { value: null },
    floatingRef: { value: null },
    floatingStyles: { value: {} },
    placement: { value: "top" },
  }),
}))

describe("FactorReferentielSwitch", () => {
  it("(a) disabled=true (forcé MVP) → switch HTML disabled", () => {
    const w = mount(FactorReferentielSwitch, { props: { disabled: true } })
    const sw = w.find('[role="switch"]')
    expect(sw.exists()).toBe(true)
    expect(sw.attributes("disabled")).toBeDefined()
    expect(sw.attributes("aria-disabled")).toBe("true")
  })

  it("(b) badge 'Estimation' visible", () => {
    const w = mount(FactorReferentielSwitch, { props: { disabled: true } })
    expect(w.text()).toContain("carbon.factorSwitch.estimateBadge")
  })

  it("(c) infobulle au survol contient carbon.factorSwitch.disabledTooltip", async () => {
    const w = mount(FactorReferentielSwitch, {
      props: { disabled: true },
      attachTo: document.body,
    })
    // Tooltip exposé via slot #content (Teleport vers body au mouseenter).
    const trigger = w.find(".ui-tooltip__trigger")
    expect(trigger.exists()).toBe(true)
    await trigger.trigger("mouseenter")
    await new Promise((r) => setTimeout(r, 150))
    expect(document.body.textContent ?? "").toContain(
      "carbon.factorSwitch.disabledTooltip",
    )
    w.unmount()
  })

  it("(d) racine porte aria-disabled=true", () => {
    const w = mount(FactorReferentielSwitch, { props: { disabled: true } })
    expect(w.attributes("aria-disabled")).toBe("true")
  })

  it("(e) labels ADEME et IPCC visibles", () => {
    const w = mount(FactorReferentielSwitch, { props: { disabled: true } })
    expect(w.text()).toContain("carbon.factorSwitch.ademeLabel")
    expect(w.text()).toContain("carbon.factorSwitch.ipccLabel")
  })
})
