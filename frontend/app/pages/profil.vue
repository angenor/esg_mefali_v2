<script setup lang="ts">
// F43 — `/profil` redirige désormais vers `/profil/entreprise`.
definePageMeta({
  middleware: ['pme-only'],
  redirect: '/profil/entreprise',
})
</script>

<template>
  <span />
</template>
