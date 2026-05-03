<script setup lang="ts">
// F38 T017 — page stub PME
definePageMeta({
  layout: 'default',
  middleware: ['pme-only'],
  breadcrumb: [{ label: 'Profil entreprise' }],
  title: 'Profil entreprise',
})
</script>

<template>
  <section class="p-6">
    <h1 class="text-2xl font-bold">Profil entreprise</h1>
    <p class="mt-2 text-gray-600">Page placeholder — éditeur livré par F08.</p>
  </section>
</template>
