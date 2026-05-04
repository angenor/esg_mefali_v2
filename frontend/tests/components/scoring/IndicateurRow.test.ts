// F46 T024 [US1] — Tests IndicateurRow (rendu minimal couvert + sources).
// Le drilldown complet est testé en US3 (T051).
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import IndicateurRow from "~/components/scoring/IndicateurRow.vue"
import type { PillarRowVM } from "~/types/scoring"

const STUBS = {
  VizSourcePin: {
    props: ["source_id", "label"],
    template: '<span class="stub-source-pin" :data-source="source_id" />',
  },
  RevokedSourceBadge: {
    props: ["sourceId"],
    template: '<span class="stub-revoked-badge" />',
  },
}

function row(overrides: Partial<PillarRowVM> = {}): PillarRowVM {
  return {
    indicateurId: "ind-1",
    indicateurCode: "EMI_GHG_ABS",
    pillar: "E",
    status: "covered",
    scoreContribution: 12.34,
    weight: 0.2,
    normalizedValue: 0.6,
    rawValue: 100,
    sourceId: "src-1",
    isSourceRevoked: false,
    isEditable: true,
    reason: null,
    ...overrides,
  }
}

describe("IndicateurRow", () => {
  it("rendu d'une PillarRowVM couverte avec VizSourcePin + score + label", () => {
    const w = mount(IndicateurRow, {
      props: { row: row() },
      global: { stubs: STUBS },
    })
    expect(w.text()).toContain("EMI_GHG_ABS")
    expect(w.text()).toContain("12.34")
    expect(w.text()).toContain("Renseigné")
    expect(w.find(".stub-source-pin").exists()).toBe(true)
    expect(w.find(".stub-source-pin").attributes("data-source")).toBe("src-1")
  })

  it("source révoquée → RevokedSourceBadge au lieu de VizSourcePin", () => {
    const w = mount(IndicateurRow, {
      props: { row: row({ isSourceRevoked: true }) },
      global: { stubs: STUBS },
    })
    expect(w.find(".stub-revoked-badge").exists()).toBe(true)
    expect(w.find(".stub-source-pin").exists()).toBe(false)
  })

  it("clic émet open(row)", async () => {
    const r = row()
    const w = mount(IndicateurRow, {
      props: { row: r },
      global: { stubs: STUBS },
    })
    await w.trigger("click")
    expect(w.emitted("open")).toBeTruthy()
    expect(w.emitted("open")![0]![0]).toEqual(r)
  })
})
