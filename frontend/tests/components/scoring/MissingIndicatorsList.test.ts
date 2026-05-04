// F46 T065 [US5] — Tests MissingIndicatorsList.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { mount } from "@vue/test-utils"
import MissingIndicatorsList from "~/components/scoring/MissingIndicatorsList.vue"
import { __resetChatEventBus } from "~/composables/useChatEventBus"
import type { MissingIndicatorVM } from "~/types/scoring"

const sample: MissingIndicatorVM[] = [
  { indicateurId: "i1", indicateurCode: "EFFECTIFS_TOTAL", pillar: "S", reason: "missing" },
  { indicateurId: "i2", indicateurCode: "GOUVERNANCE_AUDIT_INTERNE", pillar: "G", reason: "missing" },
  { indicateurId: "i3", indicateurCode: "CA_AMOUNT", pillar: "E", reason: "missing" },
]

describe("MissingIndicatorsList", () => {
  beforeEach(() => {
    __resetChatEventBus()
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("(a) missing=[] → composant masqué", () => {
    const w = mount(MissingIndicatorsList, {
      props: { missing: [], referentielCode: "BOAD" },
    })
    expect(w.find('[data-testid="missing-indicators-list"]').exists()).toBe(false)
  })

  it("(b) missing=[3] → 3 lignes + CTA Compléter chacune", () => {
    const w = mount(MissingIndicatorsList, {
      props: { missing: sample, referentielCode: "BOAD" },
    })
    const items = w.findAll(".missing-indicators__item")
    expect(items.length).toBe(3)
    expect(w.findAll('[data-testid="missing-complete-cta"]').length).toBe(3)
  })

  it("(c) clic Compléter émet 'complete(indicateurCode)'", async () => {
    const w = mount(MissingIndicatorsList, {
      props: { missing: sample, referentielCode: "BOAD" },
    })
    const cta = w.findAll('[data-testid="missing-complete-cta"]')[0]!
    await cta.trigger("click")
    const emitted = w.emitted("complete")
    expect(emitted).toBeTruthy()
    expect(emitted![0]).toEqual(["EFFECTIFS_TOTAL"])
  })

  it("(d) i18n libellés OK", () => {
    const w = mount(MissingIndicatorsList, {
      props: { missing: sample, referentielCode: "BOAD" },
    })
    expect(w.text()).toContain("À renseigner")
    expect(w.text()).toContain("Compléter")
  })
})
