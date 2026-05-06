<script setup lang="ts">
// F51 T031 — Card d'une offre dans la liste /matching.

import { computed } from "vue"
import { formatMoney } from "~/utils/moneyFormat"
import type { OffreMatchItem } from "~/types/matching"

const props = defineProps<{
  offre: OffreMatchItem
  inComparator?: boolean
  scoreVisible?: boolean
}>()

const emit = defineEmits<{
  click: [offre: OffreMatchItem]
  "add-to-comparator": [offre: OffreMatchItem]
  "remove-from-comparator": [offre: OffreMatchItem]
}>()

const montantLabel = computed(() => {
  const min = props.offre.montant_min
  const max = props.offre.montant_max
  if (!min && !max) return "Montant non spécifié"
  if (min && max) return `${formatMoney(min)} – ${formatMoney(max)}`
  if (max) return `Jusqu'à ${formatMoney(max)}`
  return `À partir de ${formatMoney(min!)}`
})

const dureeLabel = computed(() => {
  const dmin = props.offre.duree_min_mois
  const dmax = props.offre.duree_max_mois
  if (!dmin && !dmax) return "Durée flexible"
  if (dmin && dmax) return `${dmin} – ${dmax} mois`
  if (dmax) return `Jusqu'à ${dmax} mois`
  return `À partir de ${dmin} mois`
})

const typeLabel = computed(() => {
  switch (props.offre.type) {
    case "credit":
      return "Crédit"
    case "subvention":
      return "Subvention"
    case "garantie":
      return "Garantie"
    default:
      return "Autre"
  }
})

const scoreDisplay = computed(() => {
  if (!props.scoreVisible || props.offre.score === undefined) return null
  return Math.round(props.offre.score * 100)
})

function onCardClick(): void {
  emit("click", props.offre)
}

function toggleComparator(ev: Event): void {
  ev.stopPropagation()
  if (props.inComparator) emit("remove-from-comparator", props.offre)
  else emit("add-to-comparator", props.offre)
}

function onKey(ev: KeyboardEvent): void {
  if (ev.key === "Enter" || ev.key === " ") {
    ev.preventDefault()
    onCardClick()
  }
}
</script>

<template>
  <article
    role="button"
    tabindex="0"
    class="offre-card"
    :aria-label="`Offre ${offre.nom} de ${offre.intermediaire.nom}`"
    @click="onCardClick"
    @keydown="onKey"
  >
    <header class="offre-card__head">
      <h3 class="offre-card__title">{{ offre.nom }}</h3>
      <span v-if="scoreDisplay !== null" class="offre-card__score">
        Compatibilité {{ scoreDisplay }}%
      </span>
    </header>

    <div class="offre-card__intermediaire">
      <span class="offre-card__intermediaire-nom">{{ offre.intermediaire.nom }}</span>
      <span class="offre-card__type-badge" :data-type="offre.type">{{ typeLabel }}</span>
    </div>

    <dl class="offre-card__meta">
      <div>
        <dt>Montant</dt>
        <dd>{{ montantLabel }}</dd>
      </div>
      <div>
        <dt>Durée</dt>
        <dd>{{ dureeLabel }}</dd>
      </div>
    </dl>

    <ul v-if="offre.secteurs.length" class="offre-card__secteurs">
      <li v-for="s in offre.secteurs" :key="s">{{ s }}</li>
    </ul>

    <footer class="offre-card__footer">
      <button
        type="button"
        class="offre-card__compare-btn"
        :aria-pressed="inComparator"
        :class="{ 'is-active': inComparator }"
        @click="toggleComparator"
      >
        {{ inComparator ? "Retirer du comparateur" : "Ajouter au comparateur" }}
      </button>
    </footer>
  </article>
</template>

<style scoped>
.offre-card {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 0.75rem;
  background: var(--color-surface, #fff);
  cursor: pointer;
  transition: border-color 150ms, box-shadow 150ms;
}
.offre-card:hover,
.offre-card:focus-visible {
  border-color: var(--color-accent, #16a34a);
  box-shadow: 0 4px 16px -4px rgba(0, 0, 0, 0.08);
  outline: none;
}
.offre-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}
.offre-card__title {
  font-size: 1.05rem;
  font-weight: 600;
  margin: 0;
}
.offre-card__score {
  font-size: 0.8rem;
  color: var(--color-accent, #16a34a);
  font-weight: 500;
  white-space: nowrap;
}
.offre-card__intermediaire {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}
.offre-card__intermediaire-nom {
  color: var(--color-muted, #4b5563);
  font-size: 0.9rem;
}
.offre-card__type-badge {
  font-size: 0.75rem;
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  background: var(--color-muted-bg, #f3f4f6);
  color: var(--color-muted, #4b5563);
}
.offre-card__type-badge[data-type="subvention"] {
  background: #dcfce7;
  color: #15803d;
}
.offre-card__type-badge[data-type="credit"] {
  background: #dbeafe;
  color: #1d4ed8;
}
.offre-card__type-badge[data-type="garantie"] {
  background: #fef3c7;
  color: #b45309;
}
.offre-card__meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  margin: 0;
}
.offre-card__meta dt {
  font-size: 0.75rem;
  color: var(--color-muted, #6b7280);
}
.offre-card__meta dd {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 500;
}
.offre-card__secteurs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  list-style: none;
  padding: 0;
  margin: 0;
}
.offre-card__secteurs li {
  font-size: 0.75rem;
  padding: 0.1rem 0.5rem;
  background: var(--color-muted-bg, #f3f4f6);
  border-radius: 0.4rem;
  color: var(--color-muted, #4b5563);
}
.offre-card__footer {
  display: flex;
  justify-content: flex-end;
}
.offre-card__compare-btn {
  font-size: 0.85rem;
  padding: 0.4rem 0.8rem;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 0.5rem;
  background: transparent;
  cursor: pointer;
}
.offre-card__compare-btn.is-active {
  background: var(--color-accent, #16a34a);
  color: white;
  border-color: var(--color-accent, #16a34a);
}
</style>
