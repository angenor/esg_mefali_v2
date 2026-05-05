<script setup lang="ts">
// F51 T061 — Checklist documents requis avec statut joint/manquant.
import { computed } from "vue"
import { useCandidaturesStore } from "~/stores/candidatures"
import { emitCandidatureEvent } from "~/lib/candidatureEvents"
import type { DocumentChecklistItem } from "~/types/candidatures"

const store = useCandidaturesStore()
const detail = computed(() => store.detail)

const checklist = computed<DocumentChecklistItem[]>(() => {
  const requis = detail.value?.offre.documents_requis ?? []
  const links = detail.value?.draft_snapshot_json?.step3?.documents_links ?? []
  const linkByKey = new Map<string, string>()
  for (const l of links) {
    if (l.checklist_key) linkByKey.set(l.checklist_key, l.document_id)
  }
  return requis.map((r) => ({
    ...r,
    joined: linkByKey.has(r.key),
    document_id: linkByKey.get(r.key) ?? null,
  }))
})

const missingLabels = computed(() =>
  checklist.value.filter((c) => !c.joined).map((c) => c.label),
)

defineExpose({ missingLabels })

function notifyChange(key: string): void {
  emitCandidatureEvent("wizard:document:linked", {
    candidature_id: detail.value?.id ?? "",
    checklist_key: key,
  })
}
</script>

<template>
  <ul class="space-y-2">
    <li
      v-for="item in checklist"
      :key="item.key"
      class="flex items-center justify-between rounded-lg border border-gray-200 p-3"
      :class="{ 'border-emerald-300 bg-emerald-50': item.joined }"
    >
      <div class="flex items-center gap-3">
        <span
          class="flex h-6 w-6 items-center justify-center rounded-full text-xs"
          :class="
            item.joined
              ? 'bg-emerald-600 text-white'
              : 'bg-gray-200 text-gray-600'
          "
          >{{ item.joined ? "✓" : "·" }}</span
        >
        <div>
          <p class="font-medium">{{ item.label }}</p>
          <p class="text-xs text-gray-500">
            Format : {{ item.format ?? "libre" }}
          </p>
        </div>
      </div>
      <NuxtLink
        v-if="!item.joined"
        :to="`/documents?checklist_key=${encodeURIComponent(item.key)}&projet_id=${detail?.projet.id ?? ''}`"
        class="text-sm text-emerald-700 hover:underline"
        @click="notifyChange(item.key)"
        >Téléverser</NuxtLink
      >
      <span v-else class="text-xs text-emerald-700">Joint</span>
    </li>
  </ul>
</template>
