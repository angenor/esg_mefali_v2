<script setup lang="ts">
// F42 T052 — Page de connexion soignée (split-screen, Rester connecté, deep link)
import { ref } from "vue"
import PasswordVisibilityToggle from "~/components/auth/PasswordVisibilityToggle.vue"
import { useT } from "~/composables/useT"

definePageMeta({
  layout: "auth",
  public: true,
  title: "Connexion",
})

const { t } = useT()
const route = useRoute()
const router = useRouter()
const { login } = useAuth()

const email = ref("")
const password = ref("")
const rememberMe = ref(true)
const showPwd = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)
const submitting = ref(false)

if (route.query.reset === "ok") {
  successMessage.value = t("auth.login.reset_success")
}

async function onSubmit() {
  error.value = null
  submitting.value = true
  try {
    await login(
      { email: email.value, password: password.value },
      { rememberMe: rememberMe.value },
    )
    const target =
      (route.query.redirect as string) || (route.query.next as string) || "/dashboard"
    await router.push(target)
  } catch {
    error.value = t("auth.login.error")
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="space-y-6" data-testid="login-page">
    <header class="space-y-2">
      <h1 class="text-2xl font-bold">{{ t("auth.login.title") }}</h1>
      <p class="text-sm text-gray-600">{{ t("auth.login.subtitle") }}</p>
    </header>

    <p v-if="successMessage" class="text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2" role="status">
      {{ successMessage }}
    </p>

    <form class="space-y-4" @submit.prevent="onSubmit">
      <div>
        <label for="login-email" class="block text-sm font-medium">{{ t("auth.login.email") }}</label>
        <input
          id="login-email"
          v-model="email"
          type="email"
          required
          autocomplete="email"
          class="mt-1 w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-brand-500"
        />
      </div>

      <div>
        <label for="login-pwd" class="block text-sm font-medium">{{ t("auth.login.password") }}</label>
        <div class="mt-1 relative">
          <input
            id="login-pwd"
            v-model="password"
            :type="showPwd ? 'text' : 'password'"
            required
            autocomplete="current-password"
            class="w-full border rounded-lg px-3 py-2 pr-12 focus:ring-2 focus:ring-brand-500"
          />
          <div class="absolute inset-y-0 right-2 flex items-center">
            <PasswordVisibilityToggle v-model:visible="showPwd" />
          </div>
        </div>
      </div>

      <label class="flex items-center gap-2 text-sm text-gray-700">
        <input v-model="rememberMe" type="checkbox" class="h-4 w-4 rounded border-gray-300" />
        {{ t("auth.login.remember") }}
      </label>

      <p v-if="error" class="text-sm text-red-600" role="alert">{{ error }}</p>

      <button
        type="submit"
        :disabled="submitting"
        class="w-full bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg"
      >
        {{ submitting ? t("auth.login.submitting") : t("auth.login.cta") }}
      </button>
    </form>

    <div class="flex items-center justify-between text-sm">
      <NuxtLink to="/forgot-password" class="underline text-gray-700 hover:text-brand-700">
        {{ t("auth.login.forgot") }}
      </NuxtLink>
      <span>
        {{ t("auth.login.no_account") }}
        <NuxtLink to="/register" class="underline text-brand-700">
          {{ t("auth.login.create_account") }}
        </NuxtLink>
      </span>
    </div>
  </main>
</template>
