// F49 T049 — Tests composant SignatureBadge.

import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"

import SignatureBadge from "../../../app/components/rapports/verify/SignatureBadge.vue"

describe("<SignatureBadge>", () => {
  it("rend le badge ✓ vert quand valid=true", () => {
    const w = mount(SignatureBadge, { props: { valid: true, lang: "fr" } })
    const el = w.find('[data-testid="signature-badge"]')
    expect(el.exists()).toBe(true)
    expect(el.attributes("data-valid")).toBe("true")
    expect(w.text()).toContain("Signature valide")
    expect(w.text()).toContain("✓")
  })

  it("rend le badge ✗ rouge quand valid=false", () => {
    const w = mount(SignatureBadge, { props: { valid: false, lang: "fr" } })
    const el = w.find('[data-testid="signature-badge"]')
    expect(el.attributes("data-valid")).toBe("false")
    expect(w.text()).toContain("Signature invalide")
    expect(w.text()).toContain("✗")
  })

  it("rend en anglais quand lang=en", () => {
    const w = mount(SignatureBadge, { props: { valid: true, lang: "en" } })
    expect(w.text()).toContain("Valid signature")
  })
})
