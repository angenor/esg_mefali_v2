<script setup lang="ts">
// F51 T072 — Création candidature : POST /me/projets/{projet_id}/candidatures
// puis bascule vers /candidatures/{id}.
import { onMounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useCandidaturesStore } from "~/stores/candidatures"

const route = useRoute()
const router = useRouter()
const store = useCandidaturesStore()
const error = ref<string | null>(null)

onMounted(async () => {
  const offreId = String(route.query.offre_id ?? "")
  const projetId = String(route.query.projet_id ?? "")
  if (!offreId || !projetId) {
    error.value = "Paramètres `offre_id` et `projet_id` requis."
    return
  }
  const id = await store.create(projetId, offreId)
  if (id) {
    router.replace(`/candidatures/${id}`)
  } else {
    error.value = store.error ?? "Création impossible."
  }
})

useHead({ title: "Nouvelle candidature — ESG Mefali" })
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-4 p-6">
    <h1 class="text-2xl font-bold">Création de votre candidature…</h1>
    <p v-if="error" class="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ error }}
    </p>
    <p v-else class="text-sm text-gray-600">
      Préparation du dossier en cours, redirection imminente.
    </p>
  </div>
</template>
