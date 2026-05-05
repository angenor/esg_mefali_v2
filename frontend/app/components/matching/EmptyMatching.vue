<script setup lang="ts">
// F51 T033 — Empty state /matching.

defineProps<{
  hasProjet: boolean
  filtered?: boolean
}>()

const emit = defineEmits<{
  "create-projet": []
  "voir-toutes-offres": []
  reset: []
}>()
</script>

<template>
  <section class="empty-matching" aria-live="polite">
    <div class="empty-matching__visual" aria-hidden="true">
      <svg viewBox="0 0 64 64" width="80" height="80" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="32" cy="32" r="26" />
        <path d="M22 36 l8 8 l14 -18" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </div>

    <template v-if="!hasProjet">
      <h2>Découvrez des offres adaptées à vos projets verts</h2>
      <p>
        Renseignez d'abord un projet ESG pour que nous puissions vous proposer
        des financements compatibles.
      </p>
      <div class="empty-matching__actions">
        <button type="button" class="btn-primary" @click="emit('create-projet')">
          Créer mon premier projet
        </button>
        <button type="button" class="btn-secondary" @click="emit('voir-toutes-offres')">
          Voir toutes les offres
        </button>
      </div>
    </template>

    <template v-else-if="filtered">
      <h2>Aucune offre ne correspond à ces filtres</h2>
      <p>Essayez d'élargir vos critères de montant, durée ou secteur.</p>
      <div class="empty-matching__actions">
        <button type="button" class="btn-secondary" @click="emit('reset')">
          Réinitialiser les filtres
        </button>
      </div>
    </template>

    <template v-else>
      <h2>Aucune offre disponible pour ce projet</h2>
      <p>
        Le catalogue n'a pas encore d'offre compatible. Essayez le simulateur
        pour explorer ce que vous pourriez financer.
      </p>
    </template>
  </section>
</template>

<style scoped>
.empty-matching {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 3rem 1.5rem;
  gap: 1rem;
}
.empty-matching__visual {
  color: var(--color-accent, #16a34a);
  margin-bottom: 0.5rem;
}
.empty-matching h2 {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 600;
}
.empty-matching p {
  color: var(--color-muted, #4b5563);
  max-width: 36rem;
  margin: 0;
}
.empty-matching__actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  justify-content: center;
}
.btn-primary,
.btn-secondary {
  padding: 0.6rem 1.2rem;
  border-radius: 0.5rem;
  font-size: 0.95rem;
  cursor: pointer;
  border: 1px solid;
}
.btn-primary {
  background: var(--color-accent, #16a34a);
  border-color: var(--color-accent, #16a34a);
  color: white;
}
.btn-secondary {
  background: white;
  border-color: var(--color-border, #d1d5db);
  color: var(--color-text, #111827);
}
</style>
