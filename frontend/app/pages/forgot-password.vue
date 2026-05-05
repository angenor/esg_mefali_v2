<script setup lang="ts">
// F42 T054 — Page forgot password polish (anti-énumération + cooldown)
import { ref } from "vue"
import ResendCooldownButton from "~/components/auth/ResendCooldownButton.vue"
import { useT } from "~/composables/useT"

definePageMeta({
  layout: "auth",
  public: true,
  title: "Mot de passe oublié",
})

const { t } = useT()
const { forgotPassword } = useAuth()

const email = ref("")
const submitting = ref(false)
const submitted = ref(false)

async function onSubmit() {
  submitting.value = true
  try {
    await forgotPassword(email.value)
  } finally {
    submitting.value = false
    submitted.value = true
  }
}

async function resend() {
  await forgotPassword(email.value)
}
</script>

<template>
  <main class="space-y-6" data-testid="forgot-password-page">
    <header class="space-y-2">
      <h1 class="text-2xl font-bold">{{ t("auth.forgot.title") }}</h1>
      <p class="text-sm text-gray-600">{{ t("auth.forgot.subtitle") }}</p>
    </header>

    <div
      v-if="submitted"
      class="text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-3 space-y-3"
      role="status"
    >
      <p>{{ t("auth.forgot.confirmation") }}</p>
      <ResendCooldownButton :email="email" :on-send="resend" />
    </div>

    <form v-else class="space-y-4" @submit.prevent="onSubmit">
      <div>
        <label for="fp-email" class="block text-sm font-medium">{{ t("auth.forgot.email") }}</label>
        <input
          id="fp-email"
          v-model="email"
          type="email"
          required
          autocomplete="email"
          class="mt-1 w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-brand-500"
        />
      </div>
      <button
        type="submit"
        :disabled="submitting"
        class="w-full bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg"
      >
        {{ submitting ? t("auth.forgot.submitting") : t("auth.forgot.cta") }}
      </button>
    </form>

    <p class="text-sm text-center">
      <NuxtLink to="/login" class="underline text-gray-700 hover:text-brand-700">
        {{ t("auth.forgot.back_to_login") }}
      </NuxtLink>
    </p>
  </main>
</template>
