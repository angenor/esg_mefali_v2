<script setup lang="ts">
import SettingsLayout from '~/components/parametres/SettingsLayout.vue'
import SessionList from '~/components/parametres/SessionList.vue'
import ExtensionStatusCard from '~/components/parametres/ExtensionStatusCard.vue'

definePageMeta({
  layout: 'default',
  middleware: ['pme-only'],
  breadcrumb: [{ label: 'Paramètres' }, { label: 'Sécurité' }],
  title: 'Sécurité',
})
</script>

<template>
  <SettingsLayout>
    <div class="space-y-6">
      <SessionList />
      <ExtensionStatusCard />
    </div>
  </SettingsLayout>
</template>
