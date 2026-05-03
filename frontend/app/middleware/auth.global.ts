// F02 T039 / F38 T046 — Middleware global d'authentification
// Règles :
// - Pages avec `meta.public === true` : laisse passer (anonymes autorisés).
// - Pages anonymes sur routes privées → redirect /login?redirect=<path>.
// - Utilisateur authentifié sur /login ou /register → redirect /dashboard.
const AUTH_ENTRY_PATHS = new Set(["/login", "/register"])
const PUBLIC_PATH_FALLBACK = new Set([
  "/",
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
])

export default defineNuxtRouteMiddleware(async (to) => {
  if (import.meta.server) return

  const isPublic = to.meta?.public === true || PUBLIC_PATH_FALLBACK.has(to.path)
  const store = useAuthStore()

  if (!store.user && !isPublic) {
    const me = await useAuth().getMe()
    if (!me) {
      return navigateTo({
        path: "/login",
        query: { redirect: to.fullPath },
      })
    }
  }

  if (store.user && AUTH_ENTRY_PATHS.has(to.path)) {
    return navigateTo("/dashboard")
  }
})
