// F45 T056 — Tests EmptyNoGaps.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import EmptyNoGaps from "~/components/plan-action/EmptyNoGaps.vue"

describe("EmptyNoGaps", () => {
  it("affiche un titre de célébration et une description", () => {
    const w = mount(EmptyNoGaps)
    expect(w.text()).toContain("Bravo")
    expect(w.text().length).toBeGreaterThan(20)
  })

  it("aucun bouton de CTA destructif", () => {
    const w = mount(EmptyNoGaps)
    const buttons = w.findAll("button")
    // Aucun bouton dangereux : pas de "supprimer", pas de "régénérer"
    for (const b of buttons) {
      const txt = b.text().toLowerCase()
      expect(txt).not.toContain("supprim")
    }
  })

  it("rendu via UiEmptyState (role=status)", () => {
    const w = mount(EmptyNoGaps)
    expect(w.find('[role="status"]').exists()).toBe(true)
  })
})
