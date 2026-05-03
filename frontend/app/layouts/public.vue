<script setup lang="ts">
// F38 T027 — Layout public (header minimal + footer mentions)
</script>

<template>
  <div class="min-h-screen flex flex-col bg-white" data-testid="layout-public">
    <header
      class="h-14 flex items-center border-b border-gray-200 px-4"
      style="height: 56px;"
    >
      <NuxtLink to="/" class="text-lg font-bold text-brand-600" data-testid="public-logo">
        ESG Mefali
      </NuxtLink>
    </header>
    <main class="flex-1">
      <slot />
    </main>
    <footer
      class="border-t border-gray-200 bg-gray-50 px-4 py-6 text-sm text-gray-600"
      data-testid="public-footer"
    >
      <nav aria-label="Liens légaux" class="flex flex-wrap gap-4">
        <NuxtLink to="/mentions-legales" class="hover:underline">Mentions légales</NuxtLink>
        <NuxtLink to="/confidentialite" class="hover:underline">Confidentialité</NuxtLink>
        <NuxtLink to="/contact" class="hover:underline">Contact</NuxtLink>
      </nav>
    </footer>
  </div>
</template>
