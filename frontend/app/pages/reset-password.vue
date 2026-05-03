<script setup lang="ts">
// F42 T055 — Page reset password : meter + redirect login + page erreur dédiée
import { ref } from "vue"
import PasswordStrengthMeter from "~/components/auth/PasswordStrengthMeter.vue"
import PasswordVisibilityToggle from "~/components/auth/PasswordVisibilityToggle.vue"
import { usePasswordStrength } from "~/composables/usePasswordStrength"
import { useT } from "~/composables/useT"

definePageMeta({
  layout: "auth",
  public: true,
  title: "Réinitialiser le mot de passe",
})

const { t } = useT()
const route = useRoute()
const router = useRouter()
const { resetPassword } = useAuth()

const token = (route.query.token as string) || ""
const newPassword = ref("")
const newPasswordConfirm = ref("")
const showPwd = ref(false)
const submitting = ref(false)
const error = ref<string | null>(null)
const tokenInvalid = ref(!token)

const strength = usePasswordStrength(newPassword)

async function onSubmit() {
  error.value = null
  if (newPassword.value !== newPasswordConfirm.value) {
    error.value = t("auth.register.step1.password_mismatch")
    return
  }
  if (!strength.value.isAcceptable) {
    error.value = t("auth.register.step1.password_weak")
    return
  }
  submitting.value = true
  try {
    await resetPassword(token, newPassword.value)
    await router.push("/login?reset=ok")
  } catch {
    tokenInvalid.value = true
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="space-y-6" data-testid="reset-password-page">
    <template v-if="tokenInvalid">
      <header class="space-y-2">
        <h1 class="text-2xl font-bold">{{ t("auth.reset.invalid_token_title") }}</h1>
        <p class="text-sm text-gray-700">{{ t("auth.reset.invalid_token_body") }}</p>
      </header>
      <NuxtLink
        to="/forgot-password"
        class="inline-block bg-brand-600 hover:bg-brand-700 text-white font-medium px-5 py-2.5 rounded-lg"
      >
        {{ t("auth.reset.invalid_token_cta") }}
      </NuxtLink>
    </template>

    <template v-else>
      <header class="space-y-2">
        <h1 class="text-2xl font-bold">{{ t("auth.reset.title") }}</h1>
        <p class="text-sm text-gray-600">{{ t("auth.reset.subtitle") }}</p>
      </header>

      <form class="space-y-5" @submit.prevent="onSubmit">
        <div>
          <label for="rp-pwd" class="block text-sm font-medium">{{ t("auth.reset.password") }}</label>
          <div class="mt-1 relative">
            <input
              id="rp-pwd"
              v-model="newPassword"
              :type="showPwd ? 'text' : 'password'"
              required
              autocomplete="new-password"
              class="w-full border rounded-lg px-3 py-2 pr-12 focus:ring-2 focus:ring-brand-500"
            />
            <div class="absolute inset-y-0 right-2 flex items-center">
              <PasswordVisibilityToggle v-model:visible="showPwd" />
            </div>
          </div>
          <div class="mt-2">
            <PasswordStrengthMeter :password="newPassword" />
          </div>
        </div>

        <div>
          <label for="rp-pwd2" class="block text-sm font-medium">{{ t("auth.reset.password_confirm") }}</label>
          <input
            id="rp-pwd2"
            v-model="newPasswordConfirm"
            :type="showPwd ? 'text' : 'password'"
            required
            autocomplete="new-password"
            class="mt-1 w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-brand-500"
          />
        </div>

        <p v-if="error" class="text-sm text-red-600" role="alert">{{ error }}</p>

        <button
          type="submit"
          :disabled="submitting || !strength.isAcceptable"
          class="w-full bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg"
        >
          {{ submitting ? t("auth.reset.submitting") : t("auth.reset.cta") }}
        </button>
      </form>
    </template>
  </main>
</template>
