<script setup lang="ts">
import SettingsLayout from '~/components/parametres/SettingsLayout.vue'

definePageMeta({
  layout: 'default',
  middleware: ['pme-only'],
  breadcrumb: [{ label: 'Paramètres' }],
  title: 'Paramètres',
})
</script>

<template>
  <SettingsLayout>
    <section class="rounded-lg border border-gray-200 bg-white p-4">
      <h1 class="text-xl font-semibold text-gray-900">Paramètres du compte</h1>
      <p class="mt-2 text-sm text-gray-600">
        Choisissez une section dans la navigation à gauche : profil, notifications,
        consentements, sécurité, mes données ou suppression du compte.
      </p>
    </section>
  </SettingsLayout>
</template>
