<script setup lang="ts">
// F51 T039 — Page /matching/compare.

import CompareTable from "~/components/matching/CompareTable.vue"
</script>

<template>
  <main class="compare-page">
    <header class="compare-page__head">
      <NuxtLink to="/matching" class="compare-page__back">← Retour aux offres</NuxtLink>
      <h1>Comparer mes offres</h1>
    </header>
    <CompareTable />
  </main>
</template>

<style scoped>
.compare-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 1.5rem 1rem 4rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}
.compare-page__head {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.compare-page__back {
  font-size: 0.9rem;
  color: var(--color-muted, #4b5563);
  text-decoration: none;
}
.compare-page__back:hover {
  text-decoration: underline;
}
.compare-page h1 {
  margin: 0;
}
</style>
