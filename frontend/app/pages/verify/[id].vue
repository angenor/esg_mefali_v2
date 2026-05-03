<script setup lang="ts">
// F38 T031 — page de vérification publique d'attestation (stub, livré complet par F30)
definePageMeta({
  layout: "public",
  public: true,
  title: "Vérification d'attestation",
})

const route = useRoute()
const id = computed(() => route.params.id as string)
</script>

<template>
  <section class="mx-auto max-w-2xl px-4 py-12">
    <h1 class="text-2xl font-bold">Vérification d'attestation</h1>
    <p class="mt-2 text-gray-600">
      Référence : <span class="font-mono">{{ id }}</span>
    </p>
    <p class="mt-4 text-gray-600">
      Cette page publique sera complétée par la feature F30 (attestations vérifiables).
    </p>
  </section>
</template>
