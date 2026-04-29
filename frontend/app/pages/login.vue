<script setup lang="ts">
// F02 T038 — Page de connexion
const email = ref("")
const password = ref("")
const error = ref<string | null>(null)
const submitting = ref(false)
const route = useRoute()
const router = useRouter()
const { login } = useAuth()

async function onSubmit() {
  error.value = null
  submitting.value = true
  try {
    await login({ email: email.value, password: password.value })
    const next = (route.query.next as string) || "/"
    await router.push(next)
  } catch {
    error.value = "Identifiants invalides."
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="max-w-md mx-auto py-12 px-4">
    <h1 class="text-2xl font-bold mb-6">Connexion</h1>
    <form class="space-y-4" @submit.prevent="onSubmit">
      <div>
        <label for="email" class="block text-sm font-medium">Email</label>
        <input id="email" v-model="email" type="email" required autocomplete="email"
          class="mt-1 w-full border rounded px-3 py-2" />
      </div>
      <div>
        <label for="password" class="block text-sm font-medium">Mot de passe</label>
        <input id="password" v-model="password" type="password" required
          autocomplete="current-password" class="mt-1 w-full border rounded px-3 py-2" />
      </div>
      <p v-if="error" class="text-red-600 text-sm">{{ error }}</p>
      <button type="submit" :disabled="submitting"
        class="w-full bg-black text-white py-2 rounded disabled:opacity-50">
        {{ submitting ? "Connexion..." : "Se connecter" }}
      </button>
    </form>
    <p class="mt-4 text-sm">
      <NuxtLink to="/forgot-password" class="underline">Mot de passe oublié ?</NuxtLink>
      &nbsp;·&nbsp;
      <NuxtLink to="/register" class="underline">Créer un compte</NuxtLink>
    </p>
  </main>
</template>
