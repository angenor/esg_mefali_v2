<script setup lang="ts">
// F51 T071 — Détail candidature : wizard si brouillon, lecture seule sinon.
import { computed, onMounted, watch } from "vue"
import { useRoute } from "vue-router"
import { useCandidaturesStore } from "~/stores/candidatures"
import Wizard from "~/components/candidatures/Wizard.vue"
import CandidatureTimeline from "~/components/candidatures/CandidatureTimeline.vue"
import DocumentsManquantsBanner from "~/components/candidatures/DocumentsManquantsBanner.vue"

const route = useRoute()
const store = useCandidaturesStore()

const id = computed(() => String(route.params.id ?? ""))

async function load(): Promise<void> {
  if (!id.value) return
  await store.fetchDetail(id.value)
}

onMounted(load)
watch(id, load)

const detail = computed(() => store.detail)
const isDraft = computed(() => detail.value?.statut === "brouillon")

useHead(() => ({
  title: detail.value?.offre?.nom
    ? `${detail.value.offre.nom} — Candidature`
    : "Candidature",
}))

const docsMissing = computed<string[]>(() => {
  if (!detail.value) return []
  const requis = detail.value.offre?.documents_requis ?? []
  const links = detail.value.draft_snapshot_json?.step3?.documents_links ?? []
  const keys = new Set(links.map((l) => l.checklist_key))
  return requis.filter((r) => !keys.has(r.key)).map((r) => r.label)
})
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-6 p-6">
    <p v-if="store.loading" class="text-sm text-gray-500">Chargement…</p>
    <p v-else-if="!detail" class="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
      Candidature introuvable.
    </p>

    <template v-else>
      <header class="space-y-1">
        <NuxtLink to="/candidatures" class="text-sm text-emerald-700 hover:underline"
          >← Mes candidatures</NuxtLink
        >
        <h1 class="text-2xl font-bold">{{ detail.offre.nom }}</h1>
        <p class="text-sm text-gray-600">
          Statut : <strong>{{ detail.statut }}</strong>
          <span v-if="detail.submitted_at"> — Soumise le {{ new Date(detail.submitted_at).toLocaleDateString("fr-FR") }}</span>
        </p>
      </header>

      <DocumentsManquantsBanner v-if="isDraft" :missing="docsMissing" />

      <Wizard v-if="isDraft" :candidature-id="id" />

      <section v-else class="space-y-4">
        <h2 class="text-lg font-semibold">Détail figé (lecture seule)</h2>
        <pre
          class="overflow-x-auto rounded bg-gray-50 p-4 text-xs text-gray-700"
        >{{ JSON.stringify(detail.submitted_snapshot_json ?? detail.draft_snapshot_json, null, 2) }}</pre>
      </section>

      <section>
        <h2 class="text-lg font-semibold">Historique</h2>
        <CandidatureTimeline :events="detail.timeline" class="mt-3" />
      </section>
    </template>
  </div>
</template>
