<script setup lang="ts">
// F38 T067 — TheBreadcrumbs
import { useBreadcrumbs } from '~/composables/useBreadcrumbs'

const crumbs = useBreadcrumbs()

function truncate(label: string): string {
  return label.length > 40 ? label.slice(0, 37) + '…' : label
}
</script>

<template>
  <nav
    v-if="crumbs.length > 0"
    aria-label="Fil d'Ariane"
    class="hidden md:flex items-center gap-1 text-sm text-gray-600"
    data-testid="breadcrumbs"
  >
    <ol class="flex items-center gap-1">
      <li v-for="(c, idx) in crumbs" :key="idx" class="flex items-center gap-1">
        <span v-if="idx > 0" aria-hidden="true" class="text-gray-400">/</span>
        <NuxtLink
          v-if="idx < crumbs.length - 1 && c.to"
          :to="c.to"
          class="max-w-[12rem] truncate text-gray-700 hover:text-brand-700 hover:underline"
        >{{ truncate(c.label) }}</NuxtLink>
        <span
          v-else
          aria-current="page"
          class="max-w-[12rem] truncate font-medium text-gray-900"
        >{{ truncate(c.label) }}</span>
      </li>
    </ol>
  </nav>
</template>
