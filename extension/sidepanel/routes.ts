// F52 US4/US6 — Mini-routeur custom (3 vues).

export type RouteId = "candidatures" | "offers" | "chat"

export const DEFAULT_ROUTE: RouteId = "candidatures"

export const ROUTES: ReadonlyArray<RouteId> = ["candidatures", "offers", "chat"]

export function isValidRoute(value: string): value is RouteId {
  return (ROUTES as readonly string[]).includes(value)
}
