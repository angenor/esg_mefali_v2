// F44 T017 — Tests CardErrorState (role=alert, retry event).
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import CardErrorState from "~/components/dashboard/CardErrorState.vue"

describe("CardErrorState", () => {
  it("rend role=alert", () => {
    const wrapper = mount(CardErrorState, { props: { message: "Boom" } })
    expect(wrapper.attributes("role")).toBe("alert")
    expect(wrapper.text()).toContain("Boom")
  })

  it("émet 'retry' au clic sur le bouton", async () => {
    const wrapper = mount(CardErrorState, { props: { message: "X" } })
    await wrapper.find("button").trigger("click")
    expect(wrapper.emitted("retry")).toBeTruthy()
  })
})
