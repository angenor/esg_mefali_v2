<script setup lang="ts">
// F42 T068 — Bandeau persistant non bloquant si email non vérifié
import { computed, ref } from "vue"
import { storeToRefs } from "pinia"
import { useAuthStore } from "~/stores/auth"
import { useT } from "~/composables/useT"
import ResendCooldownButton from "~/components/auth/ResendCooldownButton.vue"

const { t } = useT()
const authStore = useAuthStore()
const { user } = storeToRefs(authStore)

// Repli session-only (pas de persistance)
const dismissed = ref(false)

const isUnverified = computed(() => {
  return !!user.value && user.value.email_verified_at == null
})

// Désactivation temporaire pour faciliter les tests : `NUXT_PUBLIC_DISABLE_EMAIL_VERIFICATION=true`
// dans `.env`, ou flag global `window.__DISABLE_EMAIL_VERIFICATION__ = true`.
// À retirer / contrôler plus finement avant prod.
const verificationDisabled = computed(() => {
  const cfg = useRuntimeConfig()
  const flag = (cfg.public as Record<string, unknown>).disableEmailVerification
  if (flag === true || flag === "true" || flag === "1") return true
  if (typeof window !== "undefined" && (window as { __DISABLE_EMAIL_VERIFICATION__?: boolean }).__DISABLE_EMAIL_VERIFICATION__) {
    return true
  }
  return false
})

const visible = computed(
  () => isUnverified.value && !dismissed.value && !verificationDisabled.value,
)

async function resend() {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase as string
  await $fetch(`${apiBase}/auth/email/resend`, {
    method: "POST",
    credentials: "include",
  })
}

function dismiss() {
  dismissed.value = true
}
</script>

<template>
  <aside
    v-if="visible"
    role="status"
    aria-live="polite"
    class="border-b border-amber-200 bg-amber-50 px-4 py-3 text-amber-900"
    data-testid="email-verification-banner"
  >
    <div class="mx-auto flex max-w-6xl flex-wrap items-center gap-3">
      <div class="flex-1 min-w-0">
        <p class="text-sm font-semibold">{{ t("auth.email_verification.title") }}</p>
        <p class="text-xs text-amber-800">{{ t("auth.email_verification.body") }}</p>
      </div>
      <ResendCooldownButton
        v-if="user?.email"
        :email="user.email"
        :on-send="resend"
        :label="t('auth.email_verification.resend')"
      />
      <button
        type="button"
        class="text-amber-700 hover:text-amber-900 text-sm"
        :aria-label="t('auth.email_verification.dismiss')"
        @click="dismiss"
      >
        ✕
      </button>
    </div>
  </aside>
</template>
