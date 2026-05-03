<script setup lang="ts">
// F02 T063 — Page consommation token reset password (F38 T029 : layout auth)
definePageMeta({
  layout: "auth",
  public: true,
  title: "Réinitialiser le mot de passe",
})
const route = useRoute()
const router = useRouter()
const token = (route.query.token as string) || ""
const newPassword = ref("")
const error = ref<string | null>(null)
const submitting = ref(false)
const { resetPassword } = useAuth()

async function onSubmit() {
  error.value = null
  submitting.value = true
  try {
    await resetPassword(token, newPassword.value)
    await router.push("/login")
  } catch {
    error.value = "Lien invalide ou expiré. Demandez un nouvel email."
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="max-w-md mx-auto py-12 px-4">
    <h1 class="text-2xl font-bold mb-6">Nouveau mot de passe</h1>
    <p v-if="!token" class="text-red-600">Lien invalide.</p>
    <form v-else class="space-y-4" @submit.prevent="onSubmit">
      <div>
        <label for="np" class="block text-sm font-medium">Nouveau mot de passe</label>
        <input id="np" v-model="newPassword" type="password" required minlength="12"
          class="mt-1 w-full border rounded px-3 py-2" />
        <p class="text-xs text-gray-500 mt-1">
          12 caractères min., 1 majuscule, 1 minuscule, 1 chiffre.
        </p>
      </div>
      <p v-if="error" class="text-red-600 text-sm">{{ error }}</p>
      <button type="submit" :disabled="submitting"
        class="w-full bg-black text-white py-2 rounded disabled:opacity-50">
        {{ submitting ? "Mise à jour..." : "Réinitialiser" }}
      </button>
    </form>
  </main>
</template>
