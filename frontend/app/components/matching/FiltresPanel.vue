<script setup lang="ts">
// F51 T032 — Panneau de filtres `/matching` (FR-002).

import { computed } from "vue"
import type { MatchingFilters, OffreType } from "~/types/matching"

const props = defineProps<{
  modelValue: MatchingFilters
  loading?: boolean
}>()

const emit = defineEmits<{
  "update:modelValue": [filters: MatchingFilters]
  reset: []
}>()

const TYPE_OPTIONS: { value: OffreType; label: string }[] = [
  { value: "credit", label: "Crédit" },
  { value: "subvention", label: "Subvention" },
  { value: "garantie", label: "Garantie" },
  { value: "autre", label: "Autre" },
]

function update<K extends keyof MatchingFilters>(
  key: K,
  value: MatchingFilters[K] | undefined,
): void {
  const next: MatchingFilters = { ...props.modelValue }
  if (value === undefined || value === ("" as unknown)) {
    delete next[key]
  } else {
    next[key] = value
  }
  emit("update:modelValue", next)
}

const hasFilters = computed(() => Object.keys(props.modelValue).length > 0)

function reset(): void {
  emit("update:modelValue", {})
  emit("reset")
}
</script>

<template>
  <form
    class="filtres-panel"
    role="search"
    aria-label="Filtres des offres"
    @submit.prevent
  >
    <div class="filtres-panel__row">
      <label>
        <span>Type</span>
        <select
          :value="modelValue.type ?? ''"
          @change="update('type', ($event.target as HTMLSelectElement).value as OffreType || undefined)"
        >
          <option value="">Tous</option>
          <option v-for="t in TYPE_OPTIONS" :key="t.value" :value="t.value">
            {{ t.label }}
          </option>
        </select>
      </label>

      <label>
        <span>Montant min (EUR)</span>
        <input
          type="number"
          min="0"
          step="1000"
          :value="modelValue.montant_min_eur ?? ''"
          @input="
            update(
              'montant_min_eur',
              ($event.target as HTMLInputElement).valueAsNumber || undefined,
            )
          "
        />
      </label>

      <label>
        <span>Montant max (EUR)</span>
        <input
          type="number"
          min="0"
          step="1000"
          :value="modelValue.montant_max_eur ?? ''"
          @input="
            update(
              'montant_max_eur',
              ($event.target as HTMLInputElement).valueAsNumber || undefined,
            )
          "
        />
      </label>
    </div>

    <div class="filtres-panel__row">
      <label>
        <span>Durée min (mois)</span>
        <input
          type="number"
          min="1"
          max="240"
          :value="modelValue.duree_min_mois ?? ''"
          @input="
            update(
              'duree_min_mois',
              ($event.target as HTMLInputElement).valueAsNumber || undefined,
            )
          "
        />
      </label>

      <label>
        <span>Durée max (mois)</span>
        <input
          type="number"
          min="1"
          max="240"
          :value="modelValue.duree_max_mois ?? ''"
          @input="
            update(
              'duree_max_mois',
              ($event.target as HTMLInputElement).valueAsNumber || undefined,
            )
          "
        />
      </label>

      <label>
        <span>Secteur</span>
        <input
          type="text"
          placeholder="ex. renouvelable"
          :value="modelValue.secteur ?? ''"
          @input="
            update('secteur', ($event.target as HTMLInputElement).value.trim().toLowerCase() || undefined)
          "
        />
      </label>
    </div>

    <div class="filtres-panel__row">
      <label class="filtres-panel__search">
        <span>Recherche</span>
        <input
          type="search"
          placeholder="Mot-clé (nom de l'offre, intermédiaire...)"
          :value="modelValue.q ?? ''"
          @input="update('q', ($event.target as HTMLInputElement).value || undefined)"
        />
      </label>

      <button
        v-if="hasFilters"
        type="button"
        class="filtres-panel__reset"
        :disabled="loading"
        @click="reset"
      >
        Réinitialiser
      </button>
    </div>
  </form>
</template>

<style scoped>
.filtres-panel {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--color-surface-alt, #f9fafb);
  border-radius: 0.75rem;
}
.filtres-panel__row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0.75rem;
  align-items: end;
}
.filtres-panel label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.85rem;
}
.filtres-panel input,
.filtres-panel select {
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 0.4rem;
  font-size: 0.9rem;
  background: white;
}
.filtres-panel__search {
  flex: 1;
}
.filtres-panel__reset {
  padding: 0.45rem 0.9rem;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 0.4rem;
  background: white;
  cursor: pointer;
  font-size: 0.85rem;
}
</style>
