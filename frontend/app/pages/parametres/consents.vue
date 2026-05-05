<script setup lang="ts">
import SettingsLayout from '~/components/parametres/SettingsLayout.vue'
import ConsentList from '~/components/parametres/ConsentList.vue'

definePageMeta({
  layout: 'default',
  middleware: ['pme-only'],
  breadcrumb: [{ label: 'Paramètres' }, { label: 'Consentements' }],
  title: 'Consentements',
})
</script>

<template>
  <SettingsLayout>
    <ConsentList />
  </SettingsLayout>
</template>
