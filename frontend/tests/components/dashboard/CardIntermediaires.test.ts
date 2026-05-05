// F44 T055 [US7] — Tests CardIntermediaires.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import CardIntermediaires from "~/components/dashboard/CardIntermediaires.vue"

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

const STUBS = {
  NuxtLink: { props: ["to"], template: '<a :href="to" :data-href="to"><slot/></a>' },
  UiCard: { template: "<section><slot name='header'/><slot/></section>" },
  VizLeafletMap: {
    props: ["pins", "height"],
    template: '<div class="leaflet" :data-pins="pins.length" :data-height="height"/>',
  },
}

describe("CardIntermediaires", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: "http://api" } })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("au mount → lazy-fetch /me/matching/recommendations?limit=3", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ items: [] })
    globalThis.$fetch = fetchMock
    mount(CardIntermediaires, { global: { stubs: STUBS } })
    await flushPromises()
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api/me/matching/recommendations?limit=3",
      expect.objectContaining({ credentials: "include" }),
    )
  })

  it("filled → 3 pins rendus dans VizLeafletMap + lien /matching", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue({
      items: [
        { id: "f1", label: "BOAD", type: "fond", lat: 12.6, lng: -2.5 },
        { id: "f2", label: "AFD", type: "fond", lat: 6.4, lng: 2.4 },
        { id: "b1", label: "Ecobank", type: "banque", lat: 14.7, lng: -17.4 },
      ],
    })
    const wrapper = mount(CardIntermediaires, { global: { stubs: STUBS } })
    await flushPromises()
    expect(wrapper.find(".leaflet").attributes("data-pins")).toBe("3")
    expect(wrapper.find(".leaflet").attributes("data-height")).toBe("160px")
    expect(wrapper.find('[data-testid="see-all-matching"]').attributes("data-href")).toBe("/matching")
  })

  it("empty → CTA Découvrir", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue({ items: [] })
    const wrapper = mount(CardIntermediaires, { global: { stubs: STUBS } })
    await flushPromises()
    expect(wrapper.find('a[href="/matching"]').exists()).toBe(true)
  })

  it("erreur 5xx → état error avec retry", async () => {
    globalThis.$fetch = vi.fn().mockRejectedValue(new Error("server"))
    const wrapper = mount(CardIntermediaires, { global: { stubs: STUBS } })
    await flushPromises()
    expect(wrapper.text()).toContain("server")
  })
})
