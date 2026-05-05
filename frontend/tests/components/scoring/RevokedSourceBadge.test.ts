// F46 T023 [US1] — Tests RevokedSourceBadge.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import RevokedSourceBadge from "~/components/scoring/RevokedSourceBadge.vue"

const STUBS = {
  UiBadge: {
    props: ["severity", "variant"],
    inheritAttrs: true,
    template:
      '<span class="stub-badge" :data-severity="severity" :data-variant="variant"><slot /></span>',
  },
  UiTooltip: {
    template: '<span class="stub-tooltip"><slot /><slot name="content" /></span>',
  },
}

describe("RevokedSourceBadge", () => {
  it("(a) rend UiBadge severity='warning'", () => {
    const w = mount(RevokedSourceBadge, {
      props: { sourceId: "src-123" },
      global: { stubs: STUBS },
    })
    const badge = w.find(".stub-badge")
    expect(badge.exists()).toBe(true)
    expect(badge.attributes("data-severity")).toBe("warning")
  })

  it("(b) tooltip i18n scoring.errors.revokedSource", () => {
    const w = mount(RevokedSourceBadge, {
      props: { sourceId: "src-123" },
      global: { stubs: STUBS },
    })
    expect(w.text()).toContain("Source révoquée")
  })

  it("(c) aria-label correct sur le badge", () => {
    const w = mount(RevokedSourceBadge, {
      props: { sourceId: "src-123" },
      global: { stubs: STUBS },
    })
    const badge = w.find('[data-testid="revoked-source-badge"]')
    expect(badge.exists()).toBe(true)
    expect(badge.attributes("aria-label")).toMatch(/source révoquée/i)
  })
})
