// F42 T038 — Tests useOnboardingTour (transitions d'état)
import { beforeEach, describe, expect, it, vi } from "vitest"
import { setActivePinia, createPinia } from "pinia"
import { useUserPreferencesStore } from "~/stores/userPreferences"

// Mock useRuntimeConfig (Nuxt context)
vi.mock("#imports", () => ({
  useRuntimeConfig: () => ({ public: { apiBase: "http://localhost:8010" } }),
  useCsrf: () => ({ withCsrf: () => ({}) }),
}))

vi.mock("driver.js", () => ({
  driver: () => ({
    drive: vi.fn(),
    destroy: vi.fn(),
    isLastStep: () => false,
  }),
}))

describe("useUserPreferencesStore (Pinia)", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it("a un état initial pending non chargé", () => {
    const s = useUserPreferencesStore()
    expect(s.state).toBe("pending")
    expect(s.loaded).toBe(false)
  })

  it("reset remet à zéro", () => {
    const s = useUserPreferencesStore()
    s.state = "completed"
    s.loaded = true
    s.reset()
    expect(s.state).toBe("pending")
    expect(s.loaded).toBe(false)
  })
})
