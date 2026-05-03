<script setup lang="ts">
// F38 T017 — page stub PME
definePageMeta({
  layout: 'default',
  middleware: ['pme-only'],
  breadcrumb: [{ label: 'Projets' }],
  title: 'Projets',
})
</script>

<template>
  <section class="p-6">
    <h1 class="text-2xl font-bold">Projets</h1>
    <p class="mt-2 text-gray-600">Page placeholder — liste livrée par F09.</p>
  </section>
</template>
