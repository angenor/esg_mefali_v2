// F45 T007 — Tests useActionPlanFilters.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { createPinia, setActivePinia } from "pinia"
import {
  parseFiltersFromQuery,
  serializeFiltersToQuery,
  useActionPlanFilters,
} from "../useActionPlanFilters"

declare global {
  // eslint-disable-next-line no-var
  var useRoute: unknown
  // eslint-disable-next-line no-var
  var useRouter: unknown
}

const VALID_UUID = "11111111-2222-3333-4444-555555555555"

describe("parseFiltersFromQuery", () => {
  it("parse priorité, statut, horizon valides", () => {
    const f = parseFiltersFromQuery({
      priority: "haute,moyenne",
      status: "todo",
      horizon: "12",
      responsible: VALID_UUID,
    })
    expect(f.priority).toEqual(["haute", "moyenne"])
    expect(f.status).toEqual(["todo"])
    expect(f.horizon).toBe(12)
    expect(f.responsibleUserId).toBe(VALID_UUID)
  })
  it("ignore valeurs invalides", () => {
    const f = parseFiltersFromQuery({
      priority: "zzz",
      horizon: "abc",
      responsible: "pas-un-uuid",
    })
    expect(f.priority).toEqual([])
    expect(f.horizon).toBeNull()
    expect(f.responsibleUserId).toBeNull()
  })
  it("multi-valeur priorité valide", () => {
    const f = parseFiltersFromQuery({ priority: "haute,moyenne,basse" })
    expect(f.priority).toEqual(["haute", "moyenne", "basse"])
  })
  it("absence de query → filtres vides", () => {
    expect(parseFiltersFromQuery({})).toEqual({
      priority: [],
      status: [],
      horizon: null,
      responsibleUserId: null,
    })
  })
})

describe("serializeFiltersToQuery", () => {
  it("filtres vides → objet vide", () => {
    expect(
      serializeFiltersToQuery({
        priority: [],
        status: [],
        horizon: null,
        responsibleUserId: null,
      }),
    ).toEqual({})
  })
  it("ordre stable des clés", () => {
    const q = serializeFiltersToQuery({
      priority: ["haute"],
      status: ["todo"],
      horizon: 12,
      responsibleUserId: VALID_UUID,
    })
    expect(Object.keys(q)).toEqual(["priority", "status", "horizon", "responsible"])
  })
})

describe("useActionPlanFilters", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })
  afterEach(() => {
    delete (globalThis as Record<string, unknown>).useRoute
    delete (globalThis as Record<string, unknown>).useRouter
  })

  it("hydrate les filtres depuis route.query au mount", () => {
    globalThis.useRoute = () => ({ query: { priority: "haute" } })
    globalThis.useRouter = () => ({ replace: vi.fn() })
    const f = useActionPlanFilters()
    expect(f.filters.value.priority).toEqual(["haute"])
  })

  it("setFilters met à jour le router", () => {
    const replace = vi.fn()
    globalThis.useRoute = () => ({ query: {} })
    globalThis.useRouter = () => ({ replace })
    const f = useActionPlanFilters()
    f.setFilters({ priority: ["haute"] })
    expect(replace).toHaveBeenCalledWith({ query: { priority: "haute" } })
  })

  it("resetFilters vide URL", () => {
    const replace = vi.fn()
    globalThis.useRoute = () => ({ query: { priority: "haute" } })
    globalThis.useRouter = () => ({ replace })
    const f = useActionPlanFilters()
    f.resetFilters()
    expect(f.filters.value.priority).toEqual([])
    expect(replace).toHaveBeenLastCalledWith({ query: {} })
  })
})
