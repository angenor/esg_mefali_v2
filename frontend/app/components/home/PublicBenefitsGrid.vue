<script setup lang="ts">
// F42 T073 — Grille de bénéfices page publique
import { useT } from "~/composables/useT"
const { t } = useT()

const benefits = [
  { icon: "📊", titleKey: "public.benefits.b1.title", bodyKey: "public.benefits.b1.body" },
  { icon: "💶", titleKey: "public.benefits.b2.title", bodyKey: "public.benefits.b2.body" },
  { icon: "✅", titleKey: "public.benefits.b3.title", bodyKey: "public.benefits.b3.body" },
] as const
</script>

<template>
  <section class="bg-white py-16">
    <div class="mx-auto max-w-6xl px-6">
      <h2 class="text-center text-2xl font-bold text-slate-900 md:text-3xl">
        {{ t("public.benefits.title") }}
      </h2>
      <div class="mt-10 grid grid-cols-1 gap-6 md:grid-cols-3">
        <article
          v-for="b in benefits"
          :key="b.titleKey"
          class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <div class="text-3xl" aria-hidden="true">{{ b.icon }}</div>
          <h3 class="mt-4 text-lg font-semibold text-slate-900">{{ t(b.titleKey) }}</h3>
          <p class="mt-2 text-sm text-slate-600">{{ t(b.bodyKey) }}</p>
        </article>
      </div>
    </div>
  </section>
</template>
