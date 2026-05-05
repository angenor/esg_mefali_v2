<script setup lang="ts">
// F52 US1 — Filtres /notifications (unread + kind multi-select).
import type { NotificationKind } from '~/stores/notifications'
import { useNotificationsFilters } from '~/composables/useNotificationsFilters'

const { filters, setUnreadOnly, toggleKind, reset } = useNotificationsFilters()

const KINDS: { value: NotificationKind; label: string }[] = [
  { value: 'deadline_j_minus_30', label: 'Échéance J-30' },
  { value: 'deadline_j_minus_7', label: 'Échéance J-7' },
  { value: 'deadline_j_minus_1', label: 'Échéance J-1' },
  { value: 'candidature_inactive', label: 'Candidature inactive' },
  { value: 'offre_recommandee', label: 'Offre recommandée' },
  { value: 'system', label: 'Système' },
]

function isActive(k: NotificationKind): boolean {
  return filters.value.kinds.includes(k)
}
</script>

<template>
  <section
    class="flex flex-col gap-3 rounded-lg border border-gray-200 bg-white p-3 sm:flex-row sm:items-center sm:justify-between"
    aria-label="Filtres des notifications"
  >
    <div class="flex flex-wrap items-center gap-2">
      <label class="inline-flex items-center gap-2 text-sm text-gray-700">
        <input
          type="checkbox"
          class="h-4 w-4 rounded border-gray-300 text-brand-600"
          :checked="filters.unreadOnly"
          data-testid="filter-unread-only"
          @change="(e) => setUnreadOnly((e.target as HTMLInputElement).checked)"
        />
        Non-lues uniquement
      </label>
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="k in KINDS"
          :key="k.value"
          type="button"
          class="rounded-full border px-3 py-1 text-xs"
          :class="isActive(k.value)
            ? 'border-brand-500 bg-brand-50 text-brand-700'
            : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50'"
          :aria-pressed="isActive(k.value)"
          :data-testid="`filter-kind-${k.value}`"
          @click="toggleKind(k.value)"
        >
          {{ k.label }}
        </button>
      </div>
    </div>
    <button
      type="button"
      class="self-start text-xs text-gray-500 hover:text-gray-700 sm:self-auto"
      data-testid="filter-reset"
      @click="reset"
    >
      Réinitialiser
    </button>
  </section>
</template>
