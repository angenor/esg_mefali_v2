// F43 T031 — tests ProjetCard.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import ProjetCard from "~/components/profil/ProjetCard.vue"
import type { ProjetSummary } from "~/stores/projets"

const base: ProjetSummary = {
  id: "p1",
  nom: "Mon projet",
  statut: "brouillon",
  secteur: "Énergie",
  score_esg: null,
  has_active_candidature: false,
  updated_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
}

describe("ProjetCard", () => {
  it("rend nom, secteur et statut localisé", () => {
    const wrapper = mount(ProjetCard, { props: { projet: base } })
    expect(wrapper.text()).toContain("Mon projet")
    expect(wrapper.text()).toContain("Énergie")
    expect(wrapper.text()).toContain("Brouillon")
  })

  it("score ≥ 75 → badge vert", () => {
    const wrapper = mount(ProjetCard, { props: { projet: { ...base, score_esg: 80 } } })
    const badge = wrapper.find('.projet-card__score')
    expect(badge.attributes("data-color")).toBe("vert")
  })

  it("score 50–74 → badge orange", () => {
    const wrapper = mount(ProjetCard, { props: { projet: { ...base, score_esg: 60 } } })
    expect(wrapper.find('.projet-card__score').attributes("data-color")).toBe("orange")
  })

  it("score < 50 → badge rouge", () => {
    const wrapper = mount(ProjetCard, { props: { projet: { ...base, score_esg: 30 } } })
    expect(wrapper.find('.projet-card__score').attributes("data-color")).toBe("rouge")
  })

  it("affiche sous-badge candidature en cours quand has_active_candidature=true", () => {
    const wrapper = mount(ProjetCard, {
      props: { projet: { ...base, has_active_candidature: true } },
    })
    expect(wrapper.text()).toContain("Candidature en cours")
  })

  it("calcule la date relative en heures", () => {
    const wrapper = mount(ProjetCard, { props: { projet: base } })
    expect(wrapper.text()).toMatch(/3h/)
  })

  it("statut en_recherche_financement → label localisé", () => {
    const wrapper = mount(ProjetCard, {
      props: { projet: { ...base, statut: "en_recherche_financement" } },
    })
    expect(wrapper.text()).toContain("En recherche de financement")
  })
})
