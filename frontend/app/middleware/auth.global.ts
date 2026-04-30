// F02 T039 — Middleware global d'authentification
const PUBLIC_PATHS = new Set([
  "/",
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
])

export default defineNuxtRouteMiddleware(async (to) => {
  if (PUBLIC_PATHS.has(to.path)) return
  if (import.meta.server) return

  const store = useAuthStore()
  if (!store.user) {
    const me = await useAuth().getMe()
    if (!me) {
      return navigateTo(`/login?next=${encodeURIComponent(to.fullPath)}`)
    }
  }
})
