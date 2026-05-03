// F43 T014 — tests useEntrepriseProfile (debounce, AbortController, 409, 422, retry).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { createPinia, setActivePinia } from "pinia"
import { useEntrepriseStore } from "~/stores/entreprise"
import {
  useEntrepriseProfile,
  __resetEntrepriseProfileFlushers,
} from "../useEntrepriseProfile"

class FetchError extends Error {
  statusCode: number
  data: unknown
  constructor(status: number, data: unknown) {
    super(`HTTP ${status}`)
    this.statusCode = status
    this.data = data
  }
}

function mockClient(overrides: Partial<{
  patch: ReturnType<typeof vi.fn>
  completeness: ReturnType<typeof vi.fn>
}> = {}) {
  return {
    patch:
      overrides.patch ??
      vi.fn().mockResolvedValue({
        id: "ent-1",
        account_id: "acc-1",
        version: 4,
        raison_sociale: "ACME SARL",
      }),
    completeness:
      overrides.completeness ??
      vi
        .fn()
        .mockResolvedValue({ percentage: 50, missing_required_for_features: [] }),
  }
}

function seedStore() {
  const store = useEntrepriseStore()
  store.applyData({
    id: "ent-1",
    account_id: "acc-1",
    version: 3,
    raison_sociale: "ACME SARL",
  })
  return store
}

describe("useEntrepriseProfile", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    __resetEntrepriseProfileFlushers()
  })
  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    __resetEntrepriseProfileFlushers()
  })

  it("debounce 800 ms : un seul PATCH après plusieurs setField rapides", async () => {
    seedStore()
    const client = mockClient()
    const { patchField } = useEntrepriseProfile({ client, debounceMs: 800 })

    patchField("raison_sociale", "A")
    patchField("raison_sociale", "AB")
    patchField("raison_sociale", "ABC")

    expect(client.patch).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(800)
    expect(client.patch).toHaveBeenCalledTimes(1)
    expect(client.patch).toHaveBeenLastCalledWith(
      "raison_sociale",
      "ABC",
      3,
      expect.any(AbortSignal),
    )
  })

  it("flushNow déclenche le PATCH immédiatement", async () => {
    seedStore()
    const client = mockClient()
    const { patchField, flushNow } = useEntrepriseProfile({ client, debounceMs: 800 })
    patchField("raison_sociale", "X")
    await flushNow("raison_sociale")
    expect(client.patch).toHaveBeenCalledTimes(1)
  })

  it("200 : applique data + version + completion + clear pendingChanges", async () => {
    const store = seedStore()
    const client = mockClient()
    const { patchField, flushNow } = useEntrepriseProfile({ client, debounceMs: 0 })
    patchField("raison_sociale", "Nouveau")
    await flushNow("raison_sociale")
    expect(store.version).toBe(4)
    expect(store.pendingChanges.raison_sociale).toBeUndefined()
    expect(store.completion?.percentage).toBe(50)
  })

  it("409 : ouvre un conflit avec current_version + valeur chat", async () => {
    seedStore()
    const client = mockClient({
      patch: vi
        .fn()
        .mockRejectedValue(
          new FetchError(409, {
            code: "version_conflict",
            current_version: 7,
            raison_sociale: "Chat value",
          }),
        ),
    })
    const { patchField, flushNow, conflict } = useEntrepriseProfile({
      client,
      debounceMs: 0,
    })
    patchField("raison_sociale", "Mine")
    await flushNow("raison_sociale")
    expect(conflict.value).not.toBeNull()
    expect(conflict.value?.field).toBe("raison_sociale")
    expect(conflict.value?.current_version).toBe(7)
    expect(conflict.value?.current).toBe("Chat value")
  })

  it("422 : set errors[field]", async () => {
    seedStore()
    const client = mockClient({
      patch: vi
        .fn()
        .mockRejectedValue(new FetchError(422, { detail: [{ msg: "trop court" }] })),
    })
    const { patchField, flushNow, errors } = useEntrepriseProfile({
      client,
      debounceMs: 0,
    })
    patchField("raison_sociale", "")
    await flushNow("raison_sociale")
    expect(errors.value.raison_sociale).toBe("trop court")
  })

  it("5xx : retry exponentiel jusqu'à succès", async () => {
    seedStore()
    let calls = 0
    const client = mockClient({
      patch: vi.fn().mockImplementation(() => {
        calls += 1
        if (calls < 3) return Promise.reject(new FetchError(500, {}))
        return Promise.resolve({
          id: "ent-1",
          account_id: "acc-1",
          version: 5,
          raison_sociale: "OK",
        })
      }),
    })
    const { patchField } = useEntrepriseProfile({
      client,
      debounceMs: 0,
      retryDelays: [10, 10, 10],
    })
    patchField("raison_sociale", "OK")
    await vi.advanceTimersByTimeAsync(0)
    await vi.advanceTimersByTimeAsync(10)
    await vi.advanceTimersByTimeAsync(10)
    expect(calls).toBe(3)
  })

  it("AbortController : un nouveau patchField annule le précédent en vol", async () => {
    seedStore()
    const aborted: boolean[] = []
    const client = mockClient({
      patch: vi.fn().mockImplementation(
        (_field: string, _value: unknown, _v: number, signal: AbortSignal) =>
          new Promise((_resolve, reject) => {
            signal.addEventListener("abort", () => {
              aborted.push(true)
              reject(Object.assign(new Error("aborted"), { name: "AbortError" }))
            })
          }),
      ),
    })
    const { patchField } = useEntrepriseProfile({ client, debounceMs: 0 })
    patchField("raison_sociale", "first")
    await vi.advanceTimersByTimeAsync(0)
    patchField("raison_sociale", "second")
    await vi.advanceTimersByTimeAsync(0)
    expect(aborted.length).toBe(1)
  })

  it("resolveConflict('theirs') bumpe la version et clear pending", async () => {
    seedStore()
    const store = useEntrepriseStore()
    store.setConflict({ field: "raison_sociale", your: "A", current: "B", current_version: 9 })
    store.setPendingChange("raison_sociale", "A")
    const { resolveConflict } = useEntrepriseProfile({ client: mockClient(), debounceMs: 0 })
    await resolveConflict("theirs")
    expect(store.version).toBe(9)
    expect(store.conflict).toBeNull()
    expect(store.pendingChanges.raison_sociale).toBeUndefined()
  })

  it("resolveConflict('mine') re-PATCH avec current_version", async () => {
    seedStore()
    const store = useEntrepriseStore()
    store.setConflict({ field: "raison_sociale", your: "Mine", current: "B", current_version: 9 })
    const client = mockClient()
    const { resolveConflict } = useEntrepriseProfile({ client, debounceMs: 0 })
    await resolveConflict("mine")
    expect(client.patch).toHaveBeenCalledWith(
      "raison_sociale",
      "Mine",
      9,
      expect.any(AbortSignal),
    )
    expect(store.conflict).toBeNull()
  })
})
