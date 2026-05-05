<script setup lang="ts">
// F51 T060 — Étape 2 : snapshot entreprise lecture seule.
//
// "Modifier dans profil" → ouvre /profil dans un nouvel onglet.
// "Rafraîchir snapshot" → re-fetch le détail de la candidature.
import { computed } from "vue"
import { useCandidaturesStore } from "~/stores/candidatures"

const store = useCandidaturesStore()
const detail = computed(() => store.detail)
const entreprise = computed<Record<string, unknown>>(
  () => (detail.value?.draft_snapshot_json?.step2?.entreprise as Record<string, unknown>) ?? {},
)

async function refresh(): Promise<void> {
  if (detail.value) await store.fetchDetail(detail.value.id)
}
</script>

<template>
  <section v-if="detail" class="space-y-4">
    <header class="flex items-start justify-between">
      <div>
        <h2 class="text-xl font-bold">Étape 2 — Snapshot entreprise</h2>
        <p class="mt-1 text-sm text-gray-600">
          Données figées au démarrage du wizard. Modifiez votre profil puis
          rafraîchissez si nécessaire.
        </p>
      </div>
      <div class="flex gap-2">
        <a
          href="/profil"
          target="_blank"
          rel="noopener"
          class="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50"
          >Modifier dans profil ↗</a
        >
        <button
          type="button"
          class="rounded bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700"
          @click="refresh"
        >
          Rafraîchir
        </button>
      </div>
    </header>

    <dl class="grid gap-3 rounded-lg border border-gray-200 p-4 md:grid-cols-2">
      <div v-for="(value, key) in entreprise" :key="key" class="flex flex-col">
        <dt class="text-xs font-medium uppercase text-gray-500">{{ key }}</dt>
        <dd class="text-sm text-gray-900">{{ value ?? "—" }}</dd>
      </div>
      <p v-if="!Object.keys(entreprise).length" class="text-sm text-gray-500">
        Aucun snapshot n'est encore disponible. Renseignez votre profil puis
        cliquez « Rafraîchir ».
      </p>
    </dl>
  </section>
</template>
