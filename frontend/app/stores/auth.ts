// F02 T027 — Pinia store auth (étendu F38 : logout, isAuthenticated, raison_sociale)
import { defineStore } from "pinia"

export type UserRole = "pme" | "admin"

export interface MeOut {
  user_id: string
  account_id: string | null
  role: UserRole
  email: string
  raison_sociale?: string | null
  created_at: string
  last_login_at: string | null
  email_verified_at?: string | null
}

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null as MeOut | null,
    loading: false as boolean,
  }),
  getters: {
    isAuthenticated: (s): boolean => !!s.user,
  },
  actions: {
    setUser(u: MeOut | null) {
      this.user = u
    },
    clear() {
      this.user = null
    },
    async fetchMe() {
      this.loading = true
      try {
        const config = useRuntimeConfig()
        const data = await $fetch<MeOut>(`${config.public.apiBase}/me`, {
          credentials: "include",
        })
        this.user = data
      } catch {
        this.user = null
      } finally {
        this.loading = false
      }
    },
    async logout() {
      try {
        const config = useRuntimeConfig()
        const { withCsrf } = useCsrf()
        await $fetch(`${config.public.apiBase}/auth/logout`, {
          method: "POST",
          credentials: "include",
          headers: withCsrf(),
        })
      } catch {
        // session côté serveur déjà invalide : on continue le nettoyage local
      } finally {
        this.user = null
        try {
          const notif = useNotificationsStore()
          notif.reset()
        } catch {
          // store non disponible (SSR / hors layout PME)
        }
        await navigateTo("/login")
      }
    },
  },
})
