<script setup lang="ts">
// F02 T030 — Page d'inscription PME (F38 T029 : layout auth)
definePageMeta({
  layout: "auth",
  public: true,
  title: "Créer un compte",
})
const email = ref("")
const password = ref("")
const error = ref<string | null>(null)
const submitting = ref(false)
const router = useRouter()
const { register } = useAuth()

async function onSubmit() {
  error.value = null
  submitting.value = true
  try {
    await register({ email: email.value, password: password.value })
    await router.push("/")
  } catch (e: unknown) {
    const code = (e as { data?: { detail?: { code?: string } } })?.data?.detail?.code
    if (code === "email_already_used") {
      error.value = "Cet email est déjà utilisé."
    } else {
      error.value = "Échec de l'inscription. Vérifiez votre saisie."
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="max-w-md mx-auto py-12 px-4">
    <h1 class="text-2xl font-bold mb-6">Créer un compte PME</h1>
    <form class="space-y-4" @submit.prevent="onSubmit">
      <div>
        <label for="email" class="block text-sm font-medium">Email</label>
        <input
          id="email"
          v-model="email"
          type="email"
          required
          autocomplete="email"
          class="mt-1 w-full border rounded px-3 py-2"
        />
      </div>
      <div>
        <label for="password" class="block text-sm font-medium">Mot de passe</label>
        <input
          id="password"
          v-model="password"
          type="password"
          required
          minlength="12"
          autocomplete="new-password"
          class="mt-1 w-full border rounded px-3 py-2"
        />
        <p class="text-xs text-gray-500 mt-1">
          12 caractères min., 1 majuscule, 1 minuscule, 1 chiffre.
        </p>
      </div>
      <p v-if="error" class="text-red-600 text-sm">{{ error }}</p>
      <button
        type="submit"
        :disabled="submitting"
        class="w-full bg-black text-white py-2 rounded disabled:opacity-50"
      >
        {{ submitting ? "Création..." : "Créer mon compte" }}
      </button>
    </form>
    <p class="mt-4 text-sm">
      Déjà un compte ? <NuxtLink to="/login" class="underline">Se connecter</NuxtLink>
    </p>
  </main>
</template>
