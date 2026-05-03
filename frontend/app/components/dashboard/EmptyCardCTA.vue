<script setup lang="ts">
// F44 T015 — Empty state intelligent pour cartes dashboard (cf. C-COMP-4).
// Aucun rendu de "0" sec ou "—" sec : affiche message + CTA contextuel.
interface Props {
  cta: { label: string; href: string }
  message?: string
}

const props = defineProps<Props>()
</script>

<template>
  <div class="empty-cta">
    <p v-if="props.message" class="empty-cta__message">{{ props.message }}</p>
    <slot />
    <NuxtLink :to="props.cta.href" class="empty-cta__btn">
      {{ props.cta.label }}
    </NuxtLink>
  </div>
</template>

<style scoped>
.empty-cta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem 0;
  background: linear-gradient(180deg, rgba(0, 120, 80, 0.04), transparent);
  border-radius: 0.5rem;
}
.empty-cta__message {
  color: var(--color-text-muted, #555);
  font-size: 0.875rem;
  margin: 0;
}
.empty-cta__btn {
  display: inline-block;
  padding: 0.5rem 1rem;
  background: var(--color-primary, #0a7d4d);
  color: white;
  border-radius: 0.375rem;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
}
.empty-cta__btn:hover,
.empty-cta__btn:focus-visible {
  background: var(--color-primary-dark, #0a6840);
  outline: 2px solid var(--color-focus, #0a7d4d);
  outline-offset: 2px;
}
</style>
