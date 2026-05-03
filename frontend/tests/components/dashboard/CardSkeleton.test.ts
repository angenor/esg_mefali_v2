// F44 T017 — Tests CardSkeleton (a11y aria-busy, withChart).
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import CardSkeleton from "~/components/dashboard/CardSkeleton.vue"

describe("CardSkeleton", () => {
  it("rend avec aria-busy=true", () => {
    const wrapper = mount(CardSkeleton)
    expect(wrapper.attributes("aria-busy")).toBe("true")
  })

  it("affiche zone graph quand withChart=true", () => {
    const wrapper = mount(CardSkeleton, { props: { withChart: true } })
    expect(wrapper.find(".card-skeleton__chart").exists()).toBe(true)
  })

  it("ne rend pas le chart quand withChart=false (défaut)", () => {
    const wrapper = mount(CardSkeleton)
    expect(wrapper.find(".card-skeleton__chart").exists()).toBe(false)
  })
})
