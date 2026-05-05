<script setup lang="ts">
// F51 T062 — Bandeau "documents manquants" (FR-009).
interface Props {
  missing: string[]
}
defineProps<Props>()
</script>

<template>
  <aside
    v-if="missing.length"
    class="flex items-start gap-3 rounded-lg border border-amber-300 bg-amber-50 p-4"
    role="status"
  >
    <span aria-hidden="true" class="text-2xl">⚠️</span>
    <div class="flex-1">
      <h3 class="font-semibold text-amber-900">
        {{ missing.length }} document{{ missing.length > 1 ? "s" : "" }}
        manquant{{ missing.length > 1 ? "s" : "" }}
      </h3>
      <p class="mt-1 text-sm text-amber-800">
        Téléversez les pièces requises depuis votre
        <NuxtLink to="/documents" class="underline hover:no-underline"
          >espace documents</NuxtLink
        >, puis revenez les associer à cette candidature.
      </p>
      <ul class="mt-2 list-inside list-disc text-sm text-amber-800">
        <li v-for="m in missing" :key="m">{{ m }}</li>
      </ul>
    </div>
  </aside>
</template>
