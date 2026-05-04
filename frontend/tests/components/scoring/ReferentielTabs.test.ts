// F46 T034 [US2] — Tests ReferentielTabs.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import ReferentielTabs from "~/components/scoring/ReferentielTabs.vue"

describe("ReferentielTabs", () => {
  it("(a) rend N pills selon availableCodes", () => {
    const w = mount(ReferentielTabs, {
      props: { availableCodes: ["BOAD", "CDP", "GRI"], currentCode: "BOAD" },
    })
    const tabs = w.findAll('[role="tab"]')
    expect(tabs.length).toBe(3)
    expect(tabs[0]!.text()).toContain("BOAD")
    expect(tabs[2]!.text()).toContain("GRI")
  })

  it("(b) pill currentCode a aria-selected='true'", () => {
    const w = mount(ReferentielTabs, {
      props: { availableCodes: ["BOAD", "CDP"], currentCode: "CDP" },
    })
    const tabs = w.findAll('[role="tab"]')
    expect(tabs[0]!.attributes("aria-selected")).toBe("false")
    expect(tabs[1]!.attributes("aria-selected")).toBe("true")
  })

  it("(c) clic émet select(code)", async () => {
    const w = mount(ReferentielTabs, {
      props: { availableCodes: ["BOAD", "CDP"], currentCode: "BOAD" },
    })
    await w.findAll('[role="tab"]')[1]!.trigger("click")
    expect(w.emitted("select")).toBeTruthy()
    expect(w.emitted("select")![0]).toEqual(["CDP"])
  })

  it("(d) disabled=true empêche le clic", async () => {
    const w = mount(ReferentielTabs, {
      props: {
        availableCodes: ["BOAD", "CDP"],
        currentCode: "BOAD",
        disabled: true,
      },
    })
    const tab = w.findAll('[role="tab"]')[1]!
    await tab.trigger("click")
    expect(w.emitted("select")).toBeFalsy()
    expect((tab.element as HTMLButtonElement).disabled).toBe(true)
  })
})
