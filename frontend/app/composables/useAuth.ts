// F02 T028, T037, T056, T061 — Composable auth (register, login, logout, refresh, forgot, reset)
import type { MeOut } from "~/stores/auth"
import { useAuthStore } from "~/stores/auth"

export function useAuth() {
  const config = useRuntimeConfig()
  const store = useAuthStore()
  const { withCsrf } = useCsrf()
  const apiBase = config.public.apiBase as string

  async function getMe(): Promise<MeOut | null> {
    try {
      const data = await $fetch<MeOut>(`${apiBase}/me`, { credentials: "include" })
      store.setUser(data)
      return data
    } catch {
      store.clear()
      return null
    }
  }

  async function register(payload: { email: string; password: string }): Promise<MeOut> {
    const data = await $fetch<MeOut>(`${apiBase}/auth/register`, {
      method: "POST",
      credentials: "include",
      body: payload,
    })
    store.setUser(data)
    return data
  }

  async function login(payload: { email: string; password: string }): Promise<MeOut> {
    const data = await $fetch<MeOut>(`${apiBase}/auth/login`, {
      method: "POST",
      credentials: "include",
      body: payload,
    })
    store.setUser(data)
    return data
  }

  async function logout(): Promise<void> {
    try {
      await $fetch(`${apiBase}/auth/logout`, {
        method: "POST",
        credentials: "include",
        headers: withCsrf(),
      })
    } finally {
      store.clear()
    }
  }

  async function refresh(): Promise<MeOut | null> {
    try {
      const data = await $fetch<MeOut>(`${apiBase}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: withCsrf(),
      })
      store.setUser(data)
      return data
    } catch {
      store.clear()
      return null
    }
  }

  async function forgotPassword(email: string): Promise<void> {
    await $fetch(`${apiBase}/auth/forgot-password`, {
      method: "POST",
      credentials: "include",
      body: { email },
    })
  }

  async function resetPassword(token: string, newPassword: string): Promise<void> {
    await $fetch(`${apiBase}/auth/reset-password`, {
      method: "POST",
      credentials: "include",
      body: { token, new_password: newPassword },
    })
  }

  return { getMe, register, login, logout, refresh, forgotPassword, resetPassword }
}
