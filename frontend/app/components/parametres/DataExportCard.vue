<script setup lang="ts">
// F52 US2 — Carte d'export RGPD (déclenche POST /me/exports type=rgpd_full).
import { ref } from 'vue'

const submitting = ref(false)
const lastId = ref<string | null>(null)
const error = ref<string | null>(null)

async function trigger() {
  submitting.value = true
  error.value = null
  try {
    const config = useRuntimeConfig()
    const apiBase = config.public.apiBase as string
    const { withCsrf } = useCsrf()
    const data = await $fetch<{ id: string; status: string }>(
      `${apiBase}/me/exports`,
      {
        method: 'POST',
        credentials: 'include',
        headers: withCsrf(),
        body: { type: 'rgpd_full', format: 'json' },
      }
    )
    lastId.value = data.id
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'export_failed'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="rounded-lg border border-gray-200 bg-white p-4">
    <h2 class="text-lg font-semibold text-gray-900">Export RGPD complet</h2>
    <p class="mt-1 text-xs text-gray-500">
      Téléchargez l'ensemble des données associées à votre compte au format JSON.
    </p>
    <button
      type="button"
      class="mt-3 rounded bg-brand-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
      :disabled="submitting"
      data-testid="data-export-trigger"
      @click="trigger"
    >
      {{ submitting ? 'Génération…' : 'Demander un export' }}
    </button>
    <p v-if="lastId" class="mt-2 text-xs text-gray-500">
      Demande #{{ lastId }} enregistrée — disponible dans /dashboard/exports.
    </p>
    <p v-if="error" class="mt-2 text-xs text-red-700">Échec : {{ error }}</p>
  </section>
</template>
