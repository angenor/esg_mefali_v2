<script setup lang="ts">
// F43 T041 — ProjetEmptyState : empty state + CTA « Créez votre premier projet ».
import { useT } from "~/composables/useT"

const { t } = useT()
const emit = defineEmits<{ (e: "create"): void }>()
</script>

<template>
  <section class="projet-empty" role="region" :aria-label="t('profil.projets.empty.title')">
    <div class="projet-empty__illustration" aria-hidden="true">
      <svg width="96" height="96" viewBox="0 0 96 96" fill="none">
        <circle cx="48" cy="48" r="44" fill="#dcfce7" />
        <path
          d="M30 60 L42 48 L54 56 L66 38"
          stroke="#15803d"
          stroke-width="3"
          stroke-linecap="round"
          stroke-linejoin="round"
          fill="none"
        />
      </svg>
    </div>
    <h2 class="projet-empty__title">{{ t("profil.projets.empty.title") }}</h2>
    <p class="projet-empty__body">{{ t("profil.projets.empty.body") }}</p>
    <button type="button" class="projet-empty__cta" @click="emit('create')">
      {{ t("profil.projets.empty.cta") }}
    </button>
  </section>
</template>

<style scoped>
.projet-empty {
  display: grid;
  justify-items: center;
  gap: 0.75rem;
  padding: 3rem 1.5rem;
  background: #fff;
  border: 1px dashed #cbd5e1;
  border-radius: 1rem;
  text-align: center;
}
.projet-empty__title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #0f172a;
}
.projet-empty__body {
  color: #475569;
  max-width: 32rem;
}
.projet-empty__cta {
  background: #15803d;
  color: #fff;
  border: 0;
  border-radius: 0.5rem;
  padding: 0.625rem 1.25rem;
  font-weight: 600;
  cursor: pointer;
}
.projet-empty__cta:focus-visible {
  outline: 2px solid #166534;
  outline-offset: 2px;
}
</style>
