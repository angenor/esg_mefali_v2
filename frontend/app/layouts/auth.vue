<script setup lang="ts">
// F42 T051 — Layout auth split-screen
//
// Note : les preload `/img/auth-illustration.{avif,webp}` ont été retirés
// car les fichiers ne sont pas (encore) dans `public/`. Garder un
// `<link rel="preload">` mort produit un 404 à chaque navigation et
// pollue les DevTools. Re-introduire si/quand les illustrations sont
// fournies par le design.
import { useT } from "~/composables/useT"

const { t } = useT()
</script>

<template>
  <div
    class="min-h-screen grid grid-cols-1 lg:grid-cols-2"
    data-testid="layout-auth"
  >
    <aside
      class="hidden lg:flex flex-col justify-between bg-gradient-to-br from-brand-600 to-brand-800 p-10 text-white"
      data-testid="auth-illustration"
    >
      <NuxtLink to="/" class="text-2xl font-bold">ESG Mefali</NuxtLink>
      <blockquote class="text-lg italic">
        « Donner aux PME ouest-africaines la maîtrise de leur stratégie ESG et l'accès à
        la finance verte. »
      </blockquote>
      <p class="text-sm opacity-80">{{ t("public.footer.copyright") }}</p>
    </aside>
    <main class="flex items-center justify-center px-6 py-12" data-testid="auth-main">
      <div class="w-full max-w-md">
        <slot />
      </div>
    </main>
  </div>
</template>
