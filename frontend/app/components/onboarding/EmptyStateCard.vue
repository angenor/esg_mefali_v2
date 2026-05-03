<script setup lang="ts">
// F42 T061 — Carte pédagogique pour empty state landing
interface Props {
  icon?: string
  title: string
  description: string
  linkTo?: string
}
defineProps<Props>()
</script>

<template>
  <component
    :is="linkTo ? 'NuxtLink' : 'div'"
    :to="linkTo"
    class="block rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-emerald-300 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
  >
    <div v-if="icon" class="mb-3 text-2xl" aria-hidden="true">{{ icon }}</div>
    <h3 class="text-base font-semibold text-slate-900">{{ title }}</h3>
    <p class="mt-1 text-sm text-slate-600">{{ description }}</p>
  </component>
</template>
