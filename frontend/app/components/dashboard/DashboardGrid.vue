<script setup lang="ts">
// F44 T016 — Grille responsive pour les cartes dashboard (cf. C-COMP-2).
// 1 col mobile · 2 cols tablette · 3 cols desktop ≥ 1280 px.
</script>

<template>
  <div class="dashboard-grid">
    <slot />
  </div>
</template>

<style scoped>
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}
@media (min-width: 768px) {
  .dashboard-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (min-width: 1280px) {
  .dashboard-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
.dashboard-grid > * {
  min-width: 0;
}
</style>
