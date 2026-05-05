// F51 T099 — Test perf : useSimulateurDebounce recalcule en < 200 ms perçus.
//
// Cible SC-003 : moins de 200 ms entre `flushNow()` (ou la fin du debounce)
// et la résolution du compute backend (mocké en immédiat). Mesure exclut le
// délai de debounce de 300 ms (T084) — on teste la latence applicative pure.

import { setActivePinia, createPinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { withSetup } from "../../helpers/withSetup"

const computeMock = vi.fn()

vi.mock("~/services/api/simulateur", () => ({
  simulateurApi: {
    compute: (...args: unknown[]) => computeMock(...args),
    save: vi.fn(),
    list: vi.fn(),
    softDelete: vi.fn(),
  },
}))

vi.mock("~/lib/candidatureEvents", () => ({
  emitCandidatureEvent: vi.fn(),
}))

import { useSimulateurDebounce } from "~/composables/useSimulateurDebounce"

const FAKE_RESULTS = {
  tri_pct: "10.5",
  van: { amount: "12345.67", currency: "EUR" },
  payback_mois: 48,
  cashflows: [],
  tco: { amount: "100000", currency: "EUR" },
  sources: [],
}

describe("useSimulateurDebounce — perf SC-003 (<200 ms perçus)", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    computeMock.mockReset()
    computeMock.mockResolvedValue(FAKE_RESULTS)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("flushNow() déclenche compute et résout en moins de 200 ms (mock immédiat)", async () => {
    const [{ flushNow }, app] = withSetup(() => useSimulateurDebounce())

    const t0 = performance.now()
    await flushNow()
    const elapsed = performance.now() - t0

    expect(computeMock).toHaveBeenCalledTimes(1)
    expect(elapsed).toBeLessThan(200)

    app.unmount()
  })

  it("trigger() coalesce les appels rapides en 1 seul après le debounce", async () => {
    vi.useFakeTimers()
    const [{ trigger }, app] = withSetup(() => useSimulateurDebounce(300))

    trigger()
    trigger()
    trigger()

    // Avant 300 ms : aucun appel
    await vi.advanceTimersByTimeAsync(50)
    expect(computeMock).not.toHaveBeenCalled()

    // Après 300 ms : 1 seul appel (les triggers se sont annulés mutuellement)
    await vi.advanceTimersByTimeAsync(350)
    expect(computeMock).toHaveBeenCalledTimes(1)

    app.unmount()
  })
})
