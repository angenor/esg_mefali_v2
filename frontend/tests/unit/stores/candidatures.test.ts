// F51 T014 — Store candidatures : initial state.

import { setActivePinia, createPinia } from "pinia"
import { beforeEach, describe, expect, it } from "vitest"
import { useCandidaturesStore } from "~/stores/candidatures"

describe("useCandidaturesStore", () => {
  beforeEach(() => setActivePinia(createPinia()))

  it("has clean initial state", () => {
    const s = useCandidaturesStore()
    expect(s.list).toEqual([])
    expect(s.detail).toBeNull()
    expect(s.loading).toBe(false)
    expect(s.error).toBeNull()
    expect(s.saveStatus).toBe("idle")
    expect(s.saveError).toBeNull()
    expect(s.lastSavedAt).toBeNull()
    expect(s.drafts).toEqual([])
    expect(s.submitted).toEqual([])
  })
})
