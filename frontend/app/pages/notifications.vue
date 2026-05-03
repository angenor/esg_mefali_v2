<script setup lang="ts">
definePageMeta({
  layout: 'default',
  middleware: ['pme-only'],
  breadcrumb: [{ label: 'Notifications' }],
  title: 'Notifications',
})
</script>

<template>
  <section class="p-6">
    <h1 class="text-2xl font-bold">Notifications</h1>
    <p class="mt-2 text-gray-600">Centre de notifications — détail livré par F34.</p>
  </section>
</template>
