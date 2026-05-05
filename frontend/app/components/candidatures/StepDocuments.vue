<script setup lang="ts">
// F51 T063 — Étape 3 : checklist + bannière + lien upload F50.
import { computed } from "vue"
import { useCandidaturesStore } from "~/stores/candidatures"
import DocumentsChecklist from "~/components/candidatures/DocumentsChecklist.vue"
import DocumentsManquantsBanner from "~/components/candidatures/DocumentsManquantsBanner.vue"

const store = useCandidaturesStore()
const detail = computed(() => store.detail)

const missing = computed<string[]>(() => {
  const requis = detail.value?.offre.documents_requis ?? []
  const links = detail.value?.draft_snapshot_json?.step3?.documents_links ?? []
  const keys = new Set(links.map((l) => l.checklist_key))
  return requis.filter((r) => !keys.has(r.key)).map((r) => r.label)
})
</script>

<template>
  <section v-if="detail" class="space-y-6">
    <header>
      <h2 class="text-xl font-bold">Étape 3 — Documents</h2>
      <p class="mt-1 text-sm text-gray-600">
        Téléversez les pièces requises et associez-les à cette candidature.
      </p>
    </header>

    <DocumentsManquantsBanner :missing="missing" />

    <DocumentsChecklist />
  </section>
</template>
