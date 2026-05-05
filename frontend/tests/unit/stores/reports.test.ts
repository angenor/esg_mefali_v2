// F49 T020 — Tests Pinia useReportsStore.

import { beforeEach, describe, expect, it, vi } from "vitest"
import { createPinia, setActivePinia } from "pinia"

const fetchMock = vi.fn()
;(globalThis as { $fetch?: unknown }).$fetch = fetchMock
;(globalThis as { useRuntimeConfig?: unknown }).useRuntimeConfig = () => ({
  public: { apiBase: "http://api" },
})

import { useReportsStore } from "../../../app/stores/reports"

const fakeRow = {
  rapport_id: "11111111-1111-1111-1111-111111111111",
  entity_type: "entreprise" as const,
  entity_id: "22222222-2222-2222-2222-222222222222",
  referentiels: ["ESG_MEFALI"],
  language: "fr" as const,
  file_size_bytes: 1234,
  generated_at: "2026-05-04T10:30:00Z",
  download_url: "/me/rapports/.../download",
}

describe("useReportsStore (F49)", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchMock.mockReset()
  })

  it("fetchAll peuple la table à partir des items renvoyés", async () => {
    fetchMock.mockResolvedValueOnce({ items: [fakeRow], total: 1 })
    const s = useReportsStore()
    await s.fetchAll()
    expect(s.reports).toHaveLength(1)
    expect(s.reports[0].id).toBe(fakeRow.rapport_id)
    expect(s.reports[0].status).toBe("ready")
  })

  it("generate crée une entrée pending puis transitionne en ready", async () => {
    fetchMock.mockResolvedValueOnce(fakeRow)
    const s = useReportsStore()
    const id = await s.generate({
      type: "conformite",
      referentiel_id: "ESG_MEFALI",
      period_from: "2025-01-01",
      period_to: "2025-12-31",
      entity_id: fakeRow.entity_id,
      referentiels: ["ESG_MEFALI"],
    })
    expect(id).toBe(fakeRow.rapport_id)
    expect(s.pending[id].phase).toBe("ready")
    expect(s.reports.some((r) => r.id === id)).toBe(true)
  })

  it("applyStreamEvent met à jour la phase en running puis ready", () => {
    const s = useReportsStore()
    const gid = "gen-1"
    s.pending = {
      [gid]: {
        generation_id: gid,
        phase: "pending",
        step: null,
        percent: 0,
        rapport_id: null,
        download_filename: null,
        error: null,
        last_event_id: 0,
        started_at: new Date().toISOString(),
      },
    }
    s.applyStreamEvent(gid, "progress", { step: "rendering", percent: 50 })
    expect(s.pending[gid].phase).toBe("running")
    expect(s.pending[gid].percent).toBe(50)
    s.applyStreamEvent(gid, "done", {
      rapport_id: "rid-1",
      download_filename: "x.pdf",
    })
    expect(s.pending[gid].phase).toBe("ready")
    expect(s.pending[gid].rapport_id).toBe("rid-1")
  })

  it("rehydratePending bascule les pending en running", () => {
    const s = useReportsStore()
    s.pending = {
      g1: {
        generation_id: "g1",
        phase: "pending",
        step: null,
        percent: 0,
        rapport_id: null,
        download_filename: null,
        error: null,
        last_event_id: 0,
        started_at: new Date().toISOString(),
      },
    }
    s.rehydratePending()
    expect(s.pending.g1.phase).toBe("running")
  })

  it("loadPreviewUrl met en cache et respecte expires_at", async () => {
    const exp = new Date(Date.now() + 60_000).toISOString()
    fetchMock.mockResolvedValueOnce({ url: "https://x/y", expires_at: exp })
    const s = useReportsStore()
    const out = await s.loadPreviewUrl("rid-1")
    expect(out.url).toBe("https://x/y")
    // 2nd call uses cache
    const out2 = await s.loadPreviewUrl("rid-1")
    expect(out2.url).toBe("https://x/y")
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})
