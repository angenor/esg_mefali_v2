// F52 US4 — Tests Vitest de la vue ActiveCandidaturesView.
import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import ActiveCandidaturesView from "../views/ActiveCandidaturesView.vue"

const items = [
  {
    id: "11111111-1111-4111-8111-111111111111",
    offer_label: "BOAD",
    deadline_at: new Date(Date.now() + 86_400_000).toISOString(),
    completion_pct: 50,
    resume_url: "https://x/x",
  },
]

describe("ActiveCandidaturesView.vue", () => {
  it("affiche un placeholder quand la liste est vide", () => {
    const wrapper = mount(ActiveCandidaturesView, { props: { items: [] } })
    expect(wrapper.find('[data-testid="candidatures-empty"]').exists()).toBe(true)
  })

  it("rend chaque item passé en props", () => {
    const wrapper = mount(ActiveCandidaturesView, { props: { items } })
    expect(wrapper.find(`[data-testid="candidature-${items[0].id}"]`).exists()).toBe(true)
  })
})
