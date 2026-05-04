<script setup lang="ts">
// F46 T029 [US1] / T051 [US3] — Ligne d'indicateur.
// Cf. specs/046-scoring-esg-ui/contracts/frontend-components.md §IndicateurRow.
import { computed } from "vue"
import VizSourcePin from "~/components/viz/VizSourcePin.vue"
import RevokedSourceBadge from "~/components/scoring/RevokedSourceBadge.vue"
import { useT } from "~/composables/useT"
import type { PillarRowVM } from "~/types/scoring"

interface Props {
  row: PillarRowVM
  disableEdit?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  disableEdit: false,
})

const emit = defineEmits<{
  (e: "open", row: PillarRowVM): void
}>()

const { t } = useT()

const scoreLabel = computed<string>(() => {
  if (props.row.scoreContribution === null) return "—"
  return props.row.scoreContribution.toFixed(2)
})

const statusLabel = computed<string>(() =>
  props.row.status === "covered"
    ? t("scoring.status.covered")
    : t("scoring.status.missing"),
)

const statusBadgeClass = computed<string>(() =>
  props.row.status === "covered"
    ? "indicateur-row__badge indicateur-row__badge--covered"
    : "indicateur-row__badge indicateur-row__badge--missing",
)

const showEditTooltip = computed<boolean>(
  () => !props.row.isEditable && !props.disableEdit,
)

function onClick(): void {
  emit("open", props.row)
}

function onKey(e: KeyboardEvent): void {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault()
    onClick()
  }
}
</script>

<template>
  <div
    class="indicateur-row"
    :data-status="row.status"
    :data-testid="`indicateur-row-${row.indicateurCode}`"
    :data-disabled="disableEdit ? 'true' : 'false'"
    role="button"
    tabindex="0"
    @click="onClick"
    @keydown="onKey"
  >
    <span class="indicateur-row__code">{{ row.indicateurCode }}</span>
    <span :class="statusBadgeClass" :aria-label="statusLabel">{{
      statusLabel
    }}</span>
    <span class="indicateur-row__score tabular-nums">{{ scoreLabel }}</span>
    <span class="indicateur-row__source" @click.stop>
      <RevokedSourceBadge
        v-if="row.isSourceRevoked && row.sourceId"
        :source-id="row.sourceId"
      />
      <VizSourcePin
        v-else-if="row.sourceId"
        :source_id="row.sourceId"
      />
      <span
        v-if="showEditTooltip"
        class="indicateur-row__info"
        role="img"
        :aria-label="t('scoring.overview.editTooltip')"
        :title="t('scoring.overview.editTooltip')"
        data-testid="indicateur-row-edit-tooltip"
      >ⓘ</span>
    </span>
  </div>
</template>

<style scoped>
.indicateur-row {
  display: grid;
  grid-template-columns: minmax(0, 2fr) auto minmax(3rem, auto) auto;
  align-items: center;
  gap: var(--space-3, 0.75rem);
  padding: var(--space-2, 0.5rem) var(--space-3, 0.75rem);
  border-radius: var(--radius-md, 8px);
  cursor: pointer;
  min-height: 44px;
}
.indicateur-row:hover { background: var(--color-neutral-50, #fafafa); }
.indicateur-row:focus-visible {
  outline: 2px solid var(--color-focus-ring, #3b82f6);
  outline-offset: 2px;
}
.indicateur-row[data-status="missing"] .indicateur-row__score {
  color: var(--color-text-muted, #6b7280);
}
.indicateur-row__code { font-family: var(--font-mono); font-size: var(--font-size-sm); }
.indicateur-row__badge {
  font-size: var(--font-size-xs);
  padding: 2px 8px;
  border-radius: var(--radius-sm, 4px);
}
.indicateur-row__badge--covered {
  background: var(--color-success-soft, #ecfdf5);
  color: var(--color-success-strong, #047857);
}
.indicateur-row__badge--missing {
  background: var(--color-neutral-100, #f5f5f5);
  color: var(--color-text-muted, #6b7280);
}
.indicateur-row__score {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.tabular-nums { font-variant-numeric: tabular-nums; }
.indicateur-row__info {
  margin-left: var(--space-1, 0.25rem);
  color: var(--color-text-muted, #6b7280);
  cursor: help;
}
</style>
