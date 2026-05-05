// F45 T030 — Tests StepCard.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import StepCard from "~/components/plan-action/StepCard.vue"
import type { StepCardViewModel } from "~/types/actionPlan"

function vm(o: Partial<StepCardViewModel> = {}): StepCardViewModel {
  return {
    id: "s1",
    title: "Étape 1",
    description: "Désc",
    priorityLabel: "Haute",
    priorityTone: "danger",
    horizonAt: "2026-08-01",
    horizonRelative: "Dans 3 mois",
    bucket: "lt3m",
    status: "todo",
    statusLabel: "À faire",
    statusTone: "neutral",
    responsibleUserId: null,
    responsibleAvatarUrl: null,
    responsibleLabel: "Non assigné",
    indicateurId: "ind-1",
    sourceLink: { href: "/scoring/indicateurs/ind-1", label: "Voir l'indicateur source" },
    isLoading: false,
    error: null,
    ...o,
  }
}

describe("StepCard", () => {
  it("affiche tous les champs principaux", () => {
    const w = mount(StepCard, { props: { step: vm() } })
    expect(w.text()).toContain("Étape 1")
    expect(w.text()).toContain("Désc")
    expect(w.text()).toContain("Non assigné")
    expect(w.text()).toContain("Dans 3 mois")
  })

  it("description vide → libellé Non renseigné", () => {
    const w = mount(StepCard, { props: { step: vm({ description: null }) } })
    expect(w.text()).toContain("Non renseigné")
  })

  it("checkbox émet toggle-status à done", async () => {
    const w = mount(StepCard, { props: { step: vm() } })
    await w.find("input[type=checkbox]").setValue(true)
    expect(w.emitted("toggle-status")?.[0]).toEqual(["s1", "done"])
  })

  it("bouton Modifier émet open-edit", async () => {
    const w = mount(StepCard, { props: { step: vm() } })
    await w.find(".pa-step__edit").trigger("click")
    expect(w.emitted("open-edit")?.[0]).toEqual(["s1"])
  })

  it("isLoading=true → checkbox désactivé + aria-busy", () => {
    const w = mount(StepCard, { props: { step: vm({ isLoading: true }) } })
    expect(w.find("input[type=checkbox]").attributes("disabled")).toBeDefined()
    expect(w.attributes("aria-busy")).toBe("true")
  })

  it("error → bloc role=alert visible", () => {
    const w = mount(StepCard, { props: { step: vm({ error: "Erreur réseau" }) } })
    expect(w.find('[role="alert"]').text()).toContain("Erreur réseau")
  })

  it("source pin clic émet open-source avec indicateurId", async () => {
    const w = mount(StepCard, { props: { step: vm() } })
    await w.find(".pa-step__source").trigger("click")
    expect(w.emitted("open-source")?.[0]).toEqual(["ind-1"])
  })

  it("indicateurId=null → libellé source non disponible", () => {
    const w = mount(StepCard, {
      props: { step: vm({ indicateurId: null, sourceLink: null }) },
    })
    expect(w.text()).toContain("Source non disponible")
  })

  it("indicateurId valide → pin source rendu avec href correct (T063)", () => {
    const w = mount(StepCard, { props: { step: vm() } })
    const link = w.find("a.pa-step__source")
    expect(link.exists()).toBe(true)
    expect(link.attributes("href")).toBe("/scoring/indicateurs/ind-1")
  })

  it("a11y : bouton Modifier a aria-haspopup=dialog", () => {
    const w = mount(StepCard, { props: { step: vm() } })
    expect(w.find(".pa-step__edit").attributes("aria-haspopup")).toBe("dialog")
  })
})
