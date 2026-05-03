<script setup lang="ts">
// F38 T017 — page stub PME
definePageMeta({
  layout: 'default',
  middleware: ['pme-only'],
  breadcrumb: [{ label: 'Tableau de bord' }],
  title: 'Tableau de bord',
})
</script>

<template>
  <section class="p-6">
    <h1 class="text-2xl font-bold">Tableau de bord</h1>
    <p class="mt-2 text-gray-600">Page placeholder — KPI livrés par F31.</p>
  </section>
</template>
