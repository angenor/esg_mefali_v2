// F43 T049 — tests d'intégration useEntrepriseProfile × useChatEventBus.
import { beforeEach, describe, expect, it, vi } from "vitest"
import { effectScope } from "vue"
import { setActivePinia, createPinia } from "pinia"
import { useEntrepriseProfile, __resetEntrepriseProfileFlushers } from "../useEntrepriseProfile"
import { useChatEventBus, __resetChatEventBus } from "../useChatEventBus"
import { useEntrepriseStore } from "~/stores/entreprise"

// Mock $fetch global Nuxt + useRuntimeConfig.
vi.stubGlobal(
  "useRuntimeConfig",
  () => ({ public: { apiBase: "http://localhost:8010" } }),
)

describe("useEntrepriseProfile × eventbus", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    __resetChatEventBus()
    __resetEntrepriseProfileFlushers()
  })

  it("event entity_updated sans chevauchement → re-fetch + flash (pas de conflit)", async () => {
    const store = useEntrepriseStore()
    store.applyData({ id: "e1", account_id: "a1", version: 3, raison_sociale: "Old" })

    const $fetchMock = vi.fn().mockResolvedValue({
      id: "e1",
      account_id: "a1",
      version: 4,
      raison_sociale: "New",
    })
    vi.stubGlobal("$fetch", $fetchMock)

    const scope = effectScope()
    scope.run(() => useEntrepriseProfile())

    const bus = useChatEventBus()
    bus.emit("entity_updated", {
      eventType: "entity_updated",
      entityType: "entreprise",
      entityId: "a1",
      fieldsUpdated: ["raison_sociale"],
      source: "llm",
      ts: new Date().toISOString(),
    })

    // Laisser microtasks se terminer
    await new Promise((r) => setTimeout(r, 0))
    expect($fetchMock).toHaveBeenCalled()
    expect(store.data?.raison_sociale).toBe("New")
    expect(store.conflict).toBeNull()

    scope.stop()
  })

  it("event sur champ avec édition locale en attente → ouvre conflit", async () => {
    const store = useEntrepriseStore()
    store.applyData({ id: "e1", account_id: "a1", version: 3, raison_sociale: "Old" })
    store.setPendingChange("raison_sociale", "Local edit")

    const $fetchMock = vi.fn().mockResolvedValue({
      id: "e1",
      account_id: "a1",
      version: 4,
      raison_sociale: "Chat edit",
    })
    vi.stubGlobal("$fetch", $fetchMock)

    const scope = effectScope()
    scope.run(() => useEntrepriseProfile())

    const bus = useChatEventBus()
    bus.emit("entity_updated", {
      eventType: "entity_updated",
      entityType: "entreprise",
      entityId: "a1",
      fieldsUpdated: ["raison_sociale"],
      source: "llm",
      ts: new Date().toISOString(),
    })
    await new Promise((r) => setTimeout(r, 0))

    expect(store.conflict).not.toBeNull()
    expect(store.conflict?.field).toBe("raison_sociale")
    expect(store.conflict?.your).toBe("Local edit")
    expect(store.conflict?.current).toBe("Chat edit")

    scope.stop()
  })
})
