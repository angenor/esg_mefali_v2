<script setup lang="ts">
// F38 T023 / T064 — racine de l'app
import TheRouteProgress from '~/components/shell/TheRouteProgress.vue'
import TheOfflineBanner from '~/components/shell/TheOfflineBanner.vue'

useHead({
  htmlAttrs: { lang: 'fr' },
})
</script>

<template>
  <div>
    <ClientOnly>
      <TheRouteProgress />
      <TheOfflineBanner />
    </ClientOnly>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
    <UiToastHost />
  </div>
</template>
