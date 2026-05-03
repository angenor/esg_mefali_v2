<script setup lang="ts">
// F02 T062 — Page demande de reset password (F38 T029 : layout auth)
definePageMeta({
  layout: "auth",
  public: true,
  title: "Mot de passe oublié",
})
const email = ref("")
const submitting = ref(false)
const submitted = ref(false)
const { forgotPassword } = useAuth()

async function onSubmit() {
  submitting.value = true
  try {
    await forgotPassword(email.value)
  } finally {
    submitting.value = false
    submitted.value = true
  }
}
</script>

<template>
  <main class="max-w-md mx-auto py-12 px-4">
    <h1 class="text-2xl font-bold mb-6">Mot de passe oublié</h1>
    <p v-if="submitted" class="text-green-700">
      Si cette adresse correspond à un compte, vous recevrez un email de
      réinitialisation. Vérifiez votre boîte (et les indésirables).
    </p>
    <form v-else class="space-y-4" @submit.prevent="onSubmit">
      <div>
        <label for="email" class="block text-sm font-medium">Email</label>
        <input id="email" v-model="email" type="email" required
          class="mt-1 w-full border rounded px-3 py-2" />
      </div>
      <button type="submit" :disabled="submitting"
        class="w-full bg-black text-white py-2 rounded disabled:opacity-50">
        {{ submitting ? "Envoi..." : "Envoyer" }}
      </button>
    </form>
  </main>
</template>
