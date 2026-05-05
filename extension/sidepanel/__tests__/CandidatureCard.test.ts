// F52 US4 — Tests Vitest du composant CandidatureCard.
import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import CandidatureCard from "../components/CandidatureCard.vue"

const ITEM = {
  id: "11111111-1111-4111-8111-111111111111",
  offer_label: "BOAD — Ligne verte",
  deadline_at: new Date(Date.now() + 5 * 86_400_000).toISOString(),
  completion_pct: 62,
  resume_url: "https://app.example/candidatures/x",
}

describe("CandidatureCard.vue", () => {
  it("affiche le label et le pourcentage", () => {
    const wrapper = mount(CandidatureCard, { props: { item: ITEM } })
    expect(wrapper.text()).toContain("BOAD")
    expect(wrapper.text()).toContain("62%")
  })

  it("émet open avec l'id sur click Reprendre", async () => {
    const wrapper = mount(CandidatureCard, { props: { item: ITEM } })
    await wrapper
      .find(`[data-testid="candidature-resume-${ITEM.id}"]`)
      .trigger("click")
    expect(wrapper.emitted("open")?.[0]).toEqual([ITEM.id])
  })
})
