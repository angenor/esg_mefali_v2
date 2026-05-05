// F40 T042 — VizLeafletMap tests : montage, attribution, maxZoom.
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

const STUBS = { ClientOnly: { template: '<div><slot/></div>' } }

const tileMock = { addTo: vi.fn().mockReturnThis() }
const layerMock = { addTo: vi.fn().mockReturnThis() }
const markerMock = {
  addTo: vi.fn().mockReturnThis(),
  bindTooltip: vi.fn().mockReturnThis(),
}
const mapInstance = {
  remove: vi.fn(),
}

vi.mock('leaflet', () => ({
  default: {
    map: vi.fn(() => mapInstance),
    tileLayer: vi.fn(() => tileMock),
    layerGroup: vi.fn(() => layerMock),
    marker: vi.fn(() => markerMock),
  },
}))

import VizLeafletMap from '~/components/viz/VizLeafletMap.vue'
import L from 'leaflet'

describe('VizLeafletMap', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('monte la carte côté client uniquement', async () => {
    const pins = Array.from({ length: 50 }, (_, i) => ({
      lat: 10 + i * 0.1,
      lng: -10 + i * 0.1,
      label: `pin-${i}`,
    }))
    mount(VizLeafletMap, { props: { pins, title: 'Map' }, global: { stubs: STUBS } })
    await flushPromises()
    expect((L as unknown as { map: ReturnType<typeof vi.fn> }).map).toHaveBeenCalled()
    expect((L as unknown as { tileLayer: ReturnType<typeof vi.fn> }).tileLayer).toHaveBeenCalled()
    expect((L as unknown as { marker: ReturnType<typeof vi.fn> }).marker).toHaveBeenCalledTimes(50)
  })

  it('configure maxZoom = 5 par défaut', async () => {
    mount(VizLeafletMap, { props: { pins: [{ lat: 0, lng: 0 }] }, global: { stubs: STUBS } })
    await flushPromises()
    const callArgs = (L as unknown as { map: ReturnType<typeof vi.fn> }).map.mock.calls[0]
    expect(callArgs?.[1]).toMatchObject({ maxZoom: 5 })
  })

  it('inclut l\'attribution OSM', async () => {
    mount(VizLeafletMap, { props: { pins: [{ lat: 0, lng: 0 }] }, global: { stubs: STUBS } })
    await flushPromises()
    const tileArgs = (L as unknown as { tileLayer: ReturnType<typeof vi.fn> }).tileLayer.mock.calls[0]
    expect(tileArgs?.[1]?.attribution).toContain('OpenStreetMap')
  })

  it('skip les pins hors plage', async () => {
    mount(VizLeafletMap, {
      props: { pins: [{ lat: 999, lng: 999 }, { lat: 0, lng: 0 }] },
      global: { stubs: STUBS },
    })
    await flushPromises()
    expect((L as unknown as { marker: ReturnType<typeof vi.fn> }).marker).toHaveBeenCalledTimes(1)
  })
})
