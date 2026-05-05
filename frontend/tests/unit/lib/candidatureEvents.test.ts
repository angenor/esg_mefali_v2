// F51 T012 — EventBus candidature.

import { afterEach, describe, expect, it, vi } from "vitest"
import {
  clearCandidatureEvents,
  emitCandidatureEvent,
  onCandidatureEvent,
} from "~/lib/candidatureEvents"

describe("candidatureEvents", () => {
  afterEach(() => clearCandidatureEvents())

  it("dispatches candidature:updated to subscribers", () => {
    const cb = vi.fn()
    onCandidatureEvent("candidature:updated", cb)
    emitCandidatureEvent("candidature:updated", {
      candidature_id: "abc",
      version: 5,
    })
    expect(cb).toHaveBeenCalledWith({ candidature_id: "abc", version: 5 })
  })

  it("supports wizard:step:changed", () => {
    const cb = vi.fn()
    onCandidatureEvent("wizard:step:changed", cb)
    emitCandidatureEvent("wizard:step:changed", {
      candidature_id: "x",
      from: 1,
      to: 2,
    })
    expect(cb).toHaveBeenCalledWith({ candidature_id: "x", from: 1, to: 2 })
  })

  it("unsubscribes via returned dispose", () => {
    const cb = vi.fn()
    const off = onCandidatureEvent("simulateur:saved", cb)
    off()
    emitCandidatureEvent("simulateur:saved", {
      simulation_id: "s",
      label: "L",
    })
    expect(cb).not.toHaveBeenCalled()
  })
})
