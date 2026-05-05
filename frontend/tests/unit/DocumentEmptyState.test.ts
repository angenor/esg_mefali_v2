// F50 (T013) — Tests DocumentEmptyState (FR-007b / FR-008b).

import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"

import DocumentEmptyState from "../../app/components/documents/DocumentEmptyState.vue"

describe("<DocumentEmptyState> (F50)", () => {
  it("variante entreprise affiche le titre + CTA Téléverser", () => {
    const wrapper = mount(DocumentEmptyState, { props: { context: "entreprise" } })
    expect(wrapper.text()).toContain("Aucun document pour le moment")
    const btn = wrapper.find("button")
    expect(btn.text()).toBe("Téléverser un document")
  })

  it("variante projet sans nom utilise le libellé générique", () => {
    const wrapper = mount(DocumentEmptyState, { props: { context: "projet" } })
    expect(wrapper.text()).toContain("Aucun document pour ce projet")
    expect(wrapper.find("button").text()).toBe("Ajouter au projet")
  })

  it("variante projet avec projetName cite explicitement le nom", () => {
    const wrapper = mount(DocumentEmptyState, {
      props: { context: "projet", projetName: "Solaire AKW" },
    })
    expect(wrapper.text()).toContain("Solaire AKW")
  })

  it("émet cta-click au clic sur le bouton", async () => {
    const wrapper = mount(DocumentEmptyState, { props: { context: "entreprise" } })
    await wrapper.find("button").trigger("click")
    expect(wrapper.emitted("cta-click")).toBeTruthy()
  })

  it("expose role=region et aria-label", () => {
    const wrapper = mount(DocumentEmptyState, { props: { context: "entreprise" } })
    const region = wrapper.find('[role="region"]')
    expect(region.exists()).toBe(true)
    expect(region.attributes("aria-label")).toBe("Aucun document")
  })
})
