// F46 T046 [US3] — Tests PillarAccordion.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import PillarAccordion from "~/components/scoring/PillarAccordion.vue"
import type { PillarBucketVM, PillarRowVM } from "~/types/scoring"

const STUBS = {
  IndicateurRow: {
    props: ["row", "disableEdit"],
    emits: ["open"],
    template:
      '<div class="stub-row" :data-code="row.indicateurCode" :data-disabled="String(disableEdit)" @click="$emit(\'open\', row)" />',
  },
}

function buildRow(code: string, pillar: "E" | "S" | "G" = "E"): PillarRowVM {
  return {
    indicateurId: `id-${code}`,
    indicateurCode: code,
    pillar,
    status: "covered",
    scoreContribution: 1,
    weight: 0.1,
    normalizedValue: 0.5,
    rawValue: 1,
    sourceId: `src-${code}`,
    isSourceRevoked: false,
    isEditable: true,
    reason: null,
  }
}

function buildBucket(
  pillar: "E" | "S" | "G",
  rows: PillarRowVM[],
): PillarBucketVM {
  return {
    pillar,
    pillarLabel:
      pillar === "E" ? "Environnement" : pillar === "S" ? "Social" : "Gouvernance",
    scoreByPillar: 60,
    rows,
  }
}

describe("PillarAccordion", () => {
  it("(a) rend N <details> natifs (un par pilier)", () => {
    const buckets: PillarBucketVM[] = [
      buildBucket("E", [buildRow("E1", "E")]),
      buildBucket("S", [buildRow("S1", "S")]),
      buildBucket("G", [buildRow("G1", "G")]),
    ]
    const w = mount(PillarAccordion, {
      props: { buckets },
      global: { stubs: STUBS },
    })
    expect(w.findAll("details").length).toBe(3)
  })

  it("(b) defaultOpen=['E','S','G'] ouvre les 3", () => {
    const buckets: PillarBucketVM[] = [
      buildBucket("E", [buildRow("E1", "E")]),
      buildBucket("S", [buildRow("S1", "S")]),
      buildBucket("G", [buildRow("G1", "G")]),
    ]
    const w = mount(PillarAccordion, {
      props: { buckets, defaultOpen: ["E", "S", "G"] },
      global: { stubs: STUBS },
    })
    const opened = w.findAll("details").filter((d) => d.attributes("open") !== undefined)
    expect(opened.length).toBe(3)
  })

  it("(c) bucket avec >30 rows → bouton 'Voir les N restants' + 30 rows initiales", async () => {
    const rows = Array.from({ length: 35 }, (_, i) => buildRow(`E${i}`, "E"))
    const buckets: PillarBucketVM[] = [buildBucket("E", rows)]
    const w = mount(PillarAccordion, {
      props: { buckets, defaultOpen: ["E"] },
      global: { stubs: STUBS },
    })
    expect(w.findAll(".stub-row").length).toBe(30)
    const moreBtn = w.find('[data-testid="pillar-accordion-more-E"]')
    expect(moreBtn.exists()).toBe(true)
    expect(moreBtn.text()).toContain("5")
    await moreBtn.trigger("click")
    expect(w.findAll(".stub-row").length).toBe(35)
  })

  it("(d) clic row émet openIndicateur(row)", async () => {
    const r = buildRow("E1", "E")
    const buckets: PillarBucketVM[] = [buildBucket("E", [r])]
    const w = mount(PillarAccordion, {
      props: { buckets, defaultOpen: ["E"] },
      global: { stubs: STUBS },
    })
    await w.find(".stub-row").trigger("click")
    expect(w.emitted("openIndicateur")).toBeTruthy()
    expect(w.emitted("openIndicateur")![0]![0]).toEqual(r)
  })

  it("(e) disableEdit=true est propagé aux rows", () => {
    const buckets: PillarBucketVM[] = [
      buildBucket("E", [buildRow("E1", "E")]),
    ]
    const w = mount(PillarAccordion, {
      props: { buckets, defaultOpen: ["E"], disableEdit: true },
      global: { stubs: STUBS },
    })
    expect(w.find(".stub-row").attributes("data-disabled")).toBe("true")
  })
})
