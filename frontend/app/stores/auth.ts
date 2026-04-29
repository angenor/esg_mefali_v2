// F02 T027 — Pinia store auth
import { defineStore } from "pinia"

export type UserRole = "pme" | "admin"

export interface MeOut {
  user_id: string
  account_id: string | null
  role: UserRole
  email: string
  created_at: string
  last_login_at: string | null
}

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null as MeOut | null,
    loading: false as boolean,
  }),
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
  },
})
