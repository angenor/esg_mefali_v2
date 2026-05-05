// F43 T016 — tests EntrepriseHeader.vue (binding pourcentage + tooltip champs manquants).
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import EntrepriseHeader from "~/components/profil/EntrepriseHeader.vue"

// Stubs Nuxt
const NuxtLinkStub = {
  name: "NuxtLink",
  props: ["to"],
  template: '<a :href="to"><slot /></a>',
}

describe("EntrepriseHeader", () => {
  it("affiche le pourcentage et le label localisé", () => {
    const wrapper = mount(EntrepriseHeader, {
      props: { percentage: 42, missing: [] },
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    expect(wrapper.text()).toContain("42%")
    expect(wrapper.text()).toContain("Profil entreprise")
  })

  it("rend la liste des features manquantes en tooltip", () => {
    const wrapper = mount(EntrepriseHeader, {
      props: {
        percentage: 30,
        missing: [
          { feature_code: "scoring_esg", missing_fields: ["secteur_principal", "annee_creation"] },
        ],
      },
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    const tooltip = wrapper.find(".entreprise-header__missing abbr").attributes("title")
    expect(tooltip).toContain("scoring_esg")
    expect(tooltip).toContain("secteur_principal")
  })

  it("ne rend pas de bouton 'Champs manquants' quand missing est vide", () => {
    const wrapper = mount(EntrepriseHeader, {
      props: { percentage: 100, missing: [] },
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    expect(wrapper.find(".entreprise-header__missing").exists()).toBe(false)
  })

  it("émet open-history au clic sur le bouton 'Historique'", async () => {
    const wrapper = mount(EntrepriseHeader, {
      props: { percentage: 50 },
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    await wrapper.find('[data-testid="profil-history-btn"]').trigger("click")
    expect(wrapper.emitted("open-history")).toBeTruthy()
  })
})
