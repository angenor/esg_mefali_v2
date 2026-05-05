<script setup lang="ts">
// F52 US2 — Layout commun /parametres/* avec navigation latérale.
const sections = [
  { to: '/parametres/profil', label: 'Profil' },
  { to: '/parametres/notifications', label: 'Notifications' },
  { to: '/parametres/consents', label: 'Consentements' },
  { to: '/parametres/securite', label: 'Sécurité' },
  { to: '/parametres/donnees', label: 'Mes données' },
  { to: '/parametres/suppression', label: 'Suppression du compte' },
]
</script>

<template>
  <section class="mx-auto flex max-w-5xl flex-col gap-6 p-4 sm:p-6 md:flex-row">
    <aside class="md:w-56">
      <nav aria-label="Sections paramètres" class="rounded-lg border border-gray-200 bg-white p-2">
        <NuxtLink
          v-for="s in sections"
          :key="s.to"
          :to="s.to"
          active-class="bg-brand-50 text-brand-700"
          class="block rounded px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
          :data-testid="`settings-nav-${s.to.split('/').pop()}`"
        >
          {{ s.label }}
        </NuxtLink>
      </nav>
    </aside>
    <main class="flex-1 min-w-0">
      <slot />
    </main>
  </section>
</template>
