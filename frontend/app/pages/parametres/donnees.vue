<script setup lang="ts">
import SettingsLayout from '~/components/parametres/SettingsLayout.vue'
import DataExportCard from '~/components/parametres/DataExportCard.vue'

definePageMeta({
  layout: 'default',
  middleware: ['pme-only'],
  breadcrumb: [{ label: 'Paramètres' }, { label: 'Mes données' }],
  title: 'Mes données',
})
</script>

<template>
  <SettingsLayout>
    <DataExportCard />
  </SettingsLayout>
</template>
