// F52 US4 — Tests Vitest du composant PanelHeader.
import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import PanelHeader from "../components/PanelHeader.vue"

describe("PanelHeader.vue", () => {
  it("rend les 3 onglets et marque l'actif", () => {
    const wrapper = mount(PanelHeader, {
      props: { currentRoute: "candidatures" },
    })
    expect(wrapper.find('[data-testid="tab-candidatures"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tab-offers"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tab-chat"]').exists()).toBe(true)
    expect(
      wrapper.find('[data-testid="tab-candidatures"]').attributes("aria-current")
    ).toBe("page")
  })

  it("émet navigate au clic", async () => {
    const wrapper = mount(PanelHeader, {
      props: { currentRoute: "candidatures" },
    })
    await wrapper.find('[data-testid="tab-offers"]').trigger("click")
    expect(wrapper.emitted("navigate")?.[0]).toEqual(["offers"])
  })
})
