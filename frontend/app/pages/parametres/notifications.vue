<script setup lang="ts">
import SettingsLayout from '~/components/parametres/SettingsLayout.vue'
import NotificationPreferencesGrid from '~/components/parametres/NotificationPreferencesGrid.vue'

definePageMeta({
  layout: 'default',
  middleware: ['pme-only'],
  breadcrumb: [{ label: 'Paramètres' }, { label: 'Notifications' }],
  title: 'Préférences notifications',
})
</script>

<template>
  <SettingsLayout>
    <NotificationPreferencesGrid />
  </SettingsLayout>
</template>
