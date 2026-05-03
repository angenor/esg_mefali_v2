<script setup lang="ts">
// F42 T072 — Hero page publique
import { useT } from "~/composables/useT"
const { t } = useT()
</script>

<template>
  <section class="relative overflow-hidden bg-gradient-to-br from-emerald-50 to-white">
    <div class="mx-auto max-w-6xl px-6 py-16 md:py-24">
      <div class="grid grid-cols-1 gap-10 md:grid-cols-2 md:items-center">
        <div>
          <h1 class="text-3xl font-bold leading-tight text-slate-900 md:text-5xl">
            {{ t("public.hero.title") }}
          </h1>
          <p class="mt-4 max-w-xl text-base text-slate-600 md:text-lg">
            {{ t("public.hero.subtitle") }}
          </p>
          <div class="mt-8 flex flex-wrap gap-3">
            <NuxtLink
              to="/register"
              class="inline-flex items-center justify-center rounded-xl bg-emerald-600 px-6 py-3 text-base font-semibold text-white shadow-sm transition hover:bg-emerald-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
              data-testid="public-cta-register"
            >
              {{ t("public.hero.cta") }}
            </NuxtLink>
            <NuxtLink
              to="/login"
              class="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-6 py-3 text-base font-semibold text-slate-700 transition hover:border-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
            >
              {{ t("public.hero.secondary_cta") }}
            </NuxtLink>
          </div>
        </div>
        <div class="hidden md:block" aria-hidden="true">
          <div
            class="aspect-square w-full rounded-3xl bg-gradient-to-br from-emerald-400 via-emerald-500 to-emerald-600 shadow-xl"
          />
        </div>
      </div>
    </div>
  </section>
</template>
