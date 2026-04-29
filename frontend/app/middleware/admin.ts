// F02 T051 — Middleware admin (404 si non admin pour cohérence FR-015)
export default defineNuxtRouteMiddleware(() => {
  const store = useAuthStore()
  if (!store.user || store.user.role !== "admin") {
    return abortNavigation({ statusCode: 404, message: "Page introuvable" })
  }
})
