// F38 T015 — Middleware named pme-only : interdit aux comptes admin les routes PME
export default defineNuxtRouteMiddleware(() => {
  const store = useAuthStore()
  if (store.user?.role === "admin") {
    return navigateTo("/admin")
  }
})
