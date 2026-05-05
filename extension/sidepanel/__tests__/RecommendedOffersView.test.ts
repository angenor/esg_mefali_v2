// F52 US6 — Tests Vitest de la vue RecommendedOffersView (3 cartes max).
import { mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import RecommendedOffersView from "../views/RecommendedOffersView.vue"
import type { SidepanelOfferItem } from "../lib/api"

function makeOffer(id: string, score = 0.8): SidepanelOfferItem {
  return {
    id,
    label: `Offre ${id}`,
    match_score: score,
    matching_url: `https://app.example/matching?offer=${id}`,
  }
}

describe("RecommendedOffersView.vue", () => {
  beforeEach(() => {
    ;(globalThis as unknown as { chrome?: unknown }).chrome = undefined
  })

  afterEach(() => {
    vi.restoreAllMocks()
    ;(globalThis as unknown as { chrome?: unknown }).chrome = undefined
  })

  it("affiche un état vide si aucun item", () => {
    const wrapper = mount(RecommendedOffersView, { props: { items: [] } })
    expect(wrapper.find('[data-testid="offers-empty"]').exists()).toBe(true)
  })

  it("rend au plus 3 cartes même si on lui passe plus", () => {
    const items = [
      makeOffer("a"),
      makeOffer("b"),
      makeOffer("c"),
      makeOffer("d"),
      makeOffer("e"),
    ]
    const wrapper = mount(RecommendedOffersView, { props: { items } })
    const cards = wrapper.findAll('[data-testid^="offer-"]').filter((el) => {
      const id = el.attributes("data-testid") || ""
      return /^offer-[a-z]$/.test(id)
    })
    expect(cards.length).toBe(3)
  })

  it("ouvre la matching_url via chrome.tabs.create si disponible", async () => {
    const create = vi.fn()
    ;(globalThis as unknown as {
      chrome: { tabs: { create: (opts: { url: string }) => void } }
    }).chrome = { tabs: { create } }
    const wrapper = mount(RecommendedOffersView, {
      props: { items: [makeOffer("x")] },
    })
    await wrapper.find('[data-testid="offer-open-x"]').trigger("click")
    expect(create).toHaveBeenCalledWith({
      url: "https://app.example/matching?offer=x",
    })
  })

  it("retombe sur window.open si chrome.tabs indisponible", async () => {
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null)
    const wrapper = mount(RecommendedOffersView, {
      props: { items: [makeOffer("y")] },
    })
    await wrapper.find('[data-testid="offer-open-y"]').trigger("click")
    expect(openSpy).toHaveBeenCalledWith(
      "https://app.example/matching?offer=y",
      "_blank",
      "noopener"
    )
  })
})
