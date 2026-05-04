<script setup lang="ts">
// F46 T052 [US3] — Accordéon E/S/G + indicateurs (rendu via <details> natif).
//
// Cf. specs/046-scoring-esg-ui/contracts/frontend-components.md §PillarAccordion.
import { computed, ref } from "vue"
import IndicateurRow from "~/components/scoring/IndicateurRow.vue"
import { useT } from "~/composables/useT"
import type { PillarBucketVM, PillarCode, PillarRowVM } from "~/types/scoring"

interface Props {
  buckets: PillarBucketVM[]
  defaultOpen?: PillarCode[]
  disableEdit?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  defaultOpen: () => ["E", "S", "G"],
  disableEdit: false,
})

const emit = defineEmits<{
  (e: "openIndicateur", row: PillarRowVM): void
}>()

const { t } = useT()

const ROWS_INITIAL_LIMIT = 30

// État local : expansion du bucket pour afficher les rows additionnelles.
const expandedExtraByPillar = ref<Record<string, boolean>>({})

function isExpanded(pillar: PillarCode): boolean {
  return expandedExtraByPillar.value[pillar] === true
}

function expandExtra(pillar: PillarCode): void {
  expandedExtraByPillar.value = {
    ...expandedExtraByPillar.value,
    [pillar]: true,
  }
}

const visibleRowsByPillar = computed<Record<string, PillarRowVM[]>>(() => {
  const out: Record<string, PillarRowVM[]> = {}
  for (const b of props.buckets) {
    out[b.pillar] = isExpanded(b.pillar)
      ? b.rows
      : b.rows.slice(0, ROWS_INITIAL_LIMIT)
  }
  return out
})

function isOpen(code: PillarCode): boolean {
  return props.defaultOpen.includes(code)
}

function onRowOpen(row: PillarRowVM): void {
  emit("openIndicateur", row)
}

function pillarLabelOrFallback(b: PillarBucketVM): string {
  return b.pillarLabel || String(b.pillar).toUpperCase()
}
</script>

<template>
  <section
    class="pillar-accordion"
    data-testid="pillar-accordion"
  >
    <details
      v-for="bucket in buckets"
      :key="bucket.pillar"
      class="pillar-accordion__item"
      :data-testid="`pillar-accordion-${bucket.pillar}`"
      :open="isOpen(bucket.pillar)"
    >
      <summary class="pillar-accordion__summary">
        <span class="pillar-accordion__pillar">{{ pillarLabelOrFallback(bucket) }}</span>
        <span class="pillar-accordion__score tabular-nums" v-if="bucket.scoreByPillar !== null">
          {{ bucket.scoreByPillar.toFixed(0) }}
        </span>
        <span class="pillar-accordion__count">
          {{ bucket.rows.length }}
        </span>
      </summary>

      <div class="pillar-accordion__rows" role="list">
        <IndicateurRow
          v-for="row in visibleRowsByPillar[bucket.pillar]"
          :key="row.indicateurId"
          :row="row"
          :disable-edit="disableEdit"
          role="listitem"
          @open="onRowOpen"
        />

        <button
          v-if="bucket.rows.length > 30 && !isExpanded(bucket.pillar)"
          type="button"
          class="pillar-accordion__more"
          :data-testid="`pillar-accordion-more-${bucket.pillar}`"
          @click="expandExtra(bucket.pillar)"
        >
          {{ t("scoring.buttons.viewMore", { count: bucket.rows.length - 30 }) }}
        </button>
      </div>
    </details>
  </section>
</template>

<style scoped>
.pillar-accordion {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 0.5rem);
}
.pillar-accordion__item {
  border: 1px solid var(--color-neutral-200, #e5e5e5);
  border-radius: var(--radius-md, 8px);
  background: var(--color-surface, #fff);
}
.pillar-accordion__summary {
  display: flex;
  align-items: center;
  gap: var(--space-3, 0.75rem);
  padding: var(--space-3, 0.75rem);
  cursor: pointer;
  font-weight: 600;
  list-style: none;
}
.pillar-accordion__summary::-webkit-details-marker { display: none; }
.pillar-accordion__pillar { flex: 1; }
.pillar-accordion__score {
  font-variant-numeric: tabular-nums;
  font-weight: 700;
}
.pillar-accordion__count {
  color: var(--color-text-muted, #6b7280);
  font-size: var(--font-size-sm, 0.875rem);
  font-weight: 400;
}
.pillar-accordion__rows {
  display: flex;
  flex-direction: column;
  padding: var(--space-2, 0.5rem);
  gap: var(--space-1, 0.25rem);
  border-top: 1px solid var(--color-neutral-100, #f5f5f5);
}
.pillar-accordion__more {
  font-family: inherit;
  align-self: flex-start;
  margin-top: var(--space-2, 0.5rem);
  padding: var(--space-2, 0.5rem) var(--space-3, 0.75rem);
  background: transparent;
  border: 1px dashed var(--color-neutral-300, #d4d4d4);
  border-radius: var(--radius-md, 8px);
  cursor: pointer;
  color: var(--color-text, inherit);
  font-size: var(--font-size-sm, 0.875rem);
}
.pillar-accordion__more:hover {
  background: var(--color-neutral-50, #fafafa);
}
.tabular-nums { font-variant-numeric: tabular-nums; }
</style>
