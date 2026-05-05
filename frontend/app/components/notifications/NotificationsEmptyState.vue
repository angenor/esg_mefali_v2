<script setup lang="ts">
// F52 US1 — État vide.
defineProps<{ hasFilters?: boolean }>()
</script>

<template>
  <section
    class="rounded-lg border border-dashed border-gray-200 bg-white px-6 py-12 text-center"
    data-testid="notifications-empty"
  >
    <p class="text-sm font-medium text-gray-900">
      {{ hasFilters ? 'Aucune notification ne correspond à vos filtres.' : 'Aucune notification pour le moment.' }}
    </p>
    <p class="mt-1 text-xs text-gray-500">
      Vous serez alerté(e) ici dès qu'un événement vous concerne.
    </p>
  </section>
</template>
