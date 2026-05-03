// F42 — Store Pinia des préférences utilisateur (onboarding state)
import { defineStore } from "pinia"

export type OnboardingState = "pending" | "completed" | "skipped" | "dismissed"

export interface UserPreferencesOut {
  onboarding_state: OnboardingState
  onboarding_state_updated_at: string
}

export const useUserPreferencesStore = defineStore("userPreferences", {
  state: () => ({
    state: "pending" as OnboardingState,
    updatedAt: null as string | null,
    loaded: false as boolean,
  }),
  actions: {
    async load(): Promise<void> {
      const config = useRuntimeConfig()
      const data = await $fetch<UserPreferencesOut>(
        `${config.public.apiBase}/me/preferences`,
        { credentials: "include" },
      )
      this.state = data.onboarding_state
      this.updatedAt = data.onboarding_state_updated_at
      this.loaded = true
    },
    async set(next: OnboardingState): Promise<void> {
      if (this.state === next) return
      const config = useRuntimeConfig()
      const { withCsrf } = useCsrf()
      const data = await $fetch<UserPreferencesOut>(
        `${config.public.apiBase}/me/preferences`,
        {
          method: "PATCH",
          credentials: "include",
          headers: withCsrf(),
          body: { onboarding_state: next },
        },
      )
      this.state = data.onboarding_state
      this.updatedAt = data.onboarding_state_updated_at
    },
    reset(): void {
      this.state = "pending"
      this.updatedAt = null
      this.loaded = false
    },
  },
})
