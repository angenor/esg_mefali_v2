// F38 T047 — Plugin client : intercepte les 401 globalement et redirige vers /login?expired=1
export default defineNuxtPlugin(() => {
  if (import.meta.server) return

  const original = globalThis.$fetch
  if (!original || typeof original !== 'function') return

  const wrapped = original.create({
    onResponseError({ response }: { response: { status: number } }) {
      if (response?.status === 401) {
        try {
          useAuthStore().clear()
          useNotificationsStore().reset()
        } catch {
          // stores non disponibles (premier appel SSR-side / hors layout PME)
        }
        const route = useRoute()
        // Évite la boucle si déjà sur /login
        if (route.path !== '/login') {
          void navigateTo({ path: '/login', query: { expired: '1' } })
        }
      }
    },
  })

  // Remplace globalement le helper $fetch par la version qui hooke onResponseError
  globalThis.$fetch = wrapped
})
