<script setup lang="ts">
import SettingsLayout from '~/components/parametres/SettingsLayout.vue'
import AccountDeletionDangerZone from '~/components/parametres/AccountDeletionDangerZone.vue'

definePageMeta({
  layout: 'default',
  middleware: ['pme-only'],
  breadcrumb: [{ label: 'Paramètres' }, { label: 'Suppression' }],
  title: 'Suppression du compte',
})
</script>

<template>
  <SettingsLayout>
    <AccountDeletionDangerZone />
  </SettingsLayout>
</template>
