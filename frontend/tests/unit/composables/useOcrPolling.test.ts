// F50 (T011/T089) — Tests useOcrPolling : intervalle 2 s, backoff 3/4/5,
// stop sur état terminal, timeout à 60 s, cleanup via stop().

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { useOcrPolling } from "../../../app/composables/useOcrPolling"
import type { DocumentDetail } from "../../../app/types/documents"

function makeDoc(id: string, ocr_status: DocumentDetail["ocr_status"]): DocumentDetail {
  return {
    id,
    entreprise_id: "e1",
    name: "doc.pdf",
    original_filename: "doc.pdf",
    mime_type: "application/pdf",
    size_bytes: 1234,
    type: "statuts",
    ocr_status,
    ocr_error: null,
    created_at: "2026-05-05T10:00:00Z",
    extraction_payload: { fields: [] },
    extraction_validated_at: null,
    extraction_validated_by: null,
    linked_projets: [],
    tags: [],
    deleted_at: null,
    purge_scheduled_at: null,
  }
}

describe("useOcrPolling (F50)", () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("ne démarre PAS le tick avant le premier intervalle de 2 s", async () => {
    const fetcher = vi.fn(async () => makeDoc("d1", "pending"))
    const onUpdate = vi.fn()
    useOcrPolling(fetcher).start("d1", { onUpdate })

    // Avant 2 s, aucun fetch ne doit être déclenché.
    await vi.advanceTimersByTimeAsync(1999)
    expect(fetcher).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(2)
    expect(fetcher).toHaveBeenCalledTimes(1)
    expect(onUpdate).toHaveBeenCalledWith(expect.objectContaining({ id: "d1" }))
  })

  it("continue à poller tant que ocr_status est non-terminal (pending)", async () => {
    const fetcher = vi
      .fn<(id: string) => Promise<DocumentDetail>>()
      .mockResolvedValueOnce(makeDoc("d1", "pending"))
      .mockResolvedValueOnce(makeDoc("d1", "pending"))
      .mockResolvedValueOnce(makeDoc("d1", "pending"))
    const onUpdate = vi.fn()
    useOcrPolling(fetcher).start("d1", { onUpdate })

    // Tick 1 (à 2 s) — pending, programme le tick 2 dans 3 s.
    await vi.advanceTimersByTimeAsync(2000)
    expect(fetcher).toHaveBeenCalledTimes(1)
    // Tick 2 (à 5 s) — pending, programme le tick 3 dans 4 s.
    await vi.advanceTimersByTimeAsync(3000)
    expect(fetcher).toHaveBeenCalledTimes(2)
    // Tick 3 (à 9 s).
    await vi.advanceTimersByTimeAsync(4000)
    expect(fetcher).toHaveBeenCalledTimes(3)
    expect(onUpdate).toHaveBeenCalledTimes(3)
  })

  it("continue à poller pour le statut intermédiaire processing", async () => {
    const fetcher = vi
      .fn<(id: string) => Promise<DocumentDetail>>()
      .mockResolvedValueOnce(makeDoc("d1", "processing"))
      .mockResolvedValueOnce(makeDoc("d1", "done"))
    const onUpdate = vi.fn()
    useOcrPolling(fetcher).start("d1", { onUpdate })

    await vi.advanceTimersByTimeAsync(2000) // tick 1 — processing → continue
    await vi.advanceTimersByTimeAsync(3000) // tick 2 — done → arrête
    expect(fetcher).toHaveBeenCalledTimes(2)
    expect(onUpdate).toHaveBeenLastCalledWith(
      expect.objectContaining({ ocr_status: "done" }),
    )

    // Aucun tick supplémentaire après done.
    await vi.advanceTimersByTimeAsync(10_000)
    expect(fetcher).toHaveBeenCalledTimes(2)
  })

  it("s'arrête immédiatement sur état terminal (done)", async () => {
    const fetcher = vi.fn(async () => makeDoc("d1", "done"))
    const onUpdate = vi.fn()
    const handle = useOcrPolling(fetcher).start("d1", { onUpdate })

    await vi.advanceTimersByTimeAsync(2000)
    expect(handle.isActive()).toBe(false)
    expect(fetcher).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(20_000)
    expect(fetcher).toHaveBeenCalledTimes(1)
  })

  it("s'arrête sur état terminal failed", async () => {
    const fetcher = vi.fn(async () => makeDoc("d1", "failed"))
    const onUpdate = vi.fn()
    useOcrPolling(fetcher).start("d1", { onUpdate })

    await vi.advanceTimersByTimeAsync(2000)
    expect(onUpdate).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(10_000)
    expect(fetcher).toHaveBeenCalledTimes(1)
  })

  it("s'arrête sur état terminal error", async () => {
    const fetcher = vi.fn(async () => makeDoc("d1", "error"))
    const onUpdate = vi.fn()
    useOcrPolling(fetcher).start("d1", { onUpdate })
    await vi.advanceTimersByTimeAsync(2000)
    await vi.advanceTimersByTimeAsync(10_000)
    expect(fetcher).toHaveBeenCalledTimes(1)
  })

  it("appelle onTimeout après 60 s sans état terminal", async () => {
    const fetcher = vi.fn(async () => makeDoc("d1", "pending"))
    const onUpdate = vi.fn()
    const onTimeout = vi.fn()
    useOcrPolling(fetcher).start("d1", { onUpdate, onTimeout })

    // 2 + 3 + 4 + 5 + 5 + 5 + 5 + 5 + 5 + 5 + 5 + 5 + 5 + 5 + 5 = 73 s.
    // Avant 60 s : pas de timeout.
    await vi.advanceTimersByTimeAsync(2000) // 2 s — tick 1
    await vi.advanceTimersByTimeAsync(3000) // 5 s — tick 2
    await vi.advanceTimersByTimeAsync(4000) // 9 s — tick 3
    await vi.advanceTimersByTimeAsync(5000) // 14 s — tick 4
    await vi.advanceTimersByTimeAsync(5000) // 19 s — tick 5
    expect(onTimeout).not.toHaveBeenCalled()

    // Au-delà de 60 s.
    await vi.advanceTimersByTimeAsync(50_000)
    expect(onTimeout).toHaveBeenCalledWith("d1")
    expect(onTimeout).toHaveBeenCalledTimes(1)
  })

  it("cleanup via stop() arrête immédiatement les ticks futurs", async () => {
    const fetcher = vi.fn(async () => makeDoc("d1", "pending"))
    const onUpdate = vi.fn()
    const handle = useOcrPolling(fetcher).start("d1", { onUpdate })

    await vi.advanceTimersByTimeAsync(2000)
    expect(fetcher).toHaveBeenCalledTimes(1)

    handle.stop()
    expect(handle.isActive()).toBe(false)

    // Aucun nouveau tick après stop().
    await vi.advanceTimersByTimeAsync(60_000)
    expect(fetcher).toHaveBeenCalledTimes(1)
    expect(onUpdate).toHaveBeenCalledTimes(1)
  })

  it("appelle onError sans planter le polling et continue", async () => {
    const fetcher = vi
      .fn<(id: string) => Promise<DocumentDetail>>()
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce(makeDoc("d1", "done"))
    const onUpdate = vi.fn()
    const onError = vi.fn()
    useOcrPolling(fetcher).start("d1", { onUpdate, onError })

    await vi.advanceTimersByTimeAsync(2000) // tick 1 — erreur
    expect(onError).toHaveBeenCalledTimes(1)
    expect(onError).toHaveBeenCalledWith("d1", expect.any(Error))

    await vi.advanceTimersByTimeAsync(3000) // tick 2 — done
    expect(onUpdate).toHaveBeenCalledWith(
      expect.objectContaining({ ocr_status: "done" }),
    )
  })

  it("ne déclenche plus onUpdate si stop() est appelé pendant un fetch in-flight", async () => {
    let resolveFetch: (d: DocumentDetail) => void = () => undefined
    const fetcher = vi.fn(
      () => new Promise<DocumentDetail>((res) => (resolveFetch = res)),
    )
    const onUpdate = vi.fn()
    const handle = useOcrPolling(fetcher).start("d1", { onUpdate })

    await vi.advanceTimersByTimeAsync(2000)
    expect(fetcher).toHaveBeenCalledTimes(1)

    // Stop avant la résolution du fetch.
    handle.stop()
    resolveFetch(makeDoc("d1", "pending"))
    await vi.advanceTimersByTimeAsync(0)
    expect(onUpdate).not.toHaveBeenCalled()
  })
})
