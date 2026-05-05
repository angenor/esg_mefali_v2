<script setup lang="ts">
// F46 T053 [US3] — Drawer indicateur (slide-in droite avec graphique 12 mois).
//
// Cf. specs/046-scoring-esg-ui/contracts/frontend-components.md §IndicateurDrawer.
// Perf R9 : <VizLineChart> n'est monté que si open === true.
import { computed, nextTick, ref, watch } from "vue"
import VizLineChart from "~/components/viz/VizLineChart.vue"
import VizSourcePin from "~/components/viz/VizSourcePin.vue"
import RevokedSourceBadge from "~/components/scoring/RevokedSourceBadge.vue"
import { useT } from "~/composables/useT"
import { useFocusTrap } from "~/composables/useFocusTrap"
import { useScoringHistory } from "~/composables/useScoringHistory"
import type { PillarRowVM } from "~/types/scoring"

interface Props {
  row: PillarRowVM | null
  referentielCode: string
  open?: boolean
  disableEdit?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  open: false,
  disableEdit: false,
})

const emit = defineEmits<{
  (e: "close"): void
  (e: "edit", row: PillarRowVM): void
}>()

const { t } = useT()

const drawerRef = ref<HTMLElement | null>(null)
const focusTrap = useFocusTrap(drawerRef)

// History API : load uniquement quand open=true.
const history = useScoringHistory(props.referentielCode)

const editDisabled = computed<boolean>(() => {
  if (props.disableEdit) return true
  if (!props.row) return true
  return !props.row.isEditable
})

const valueLabel = computed<string>(() => {
  if (!props.row) return "—"
  if (props.row.rawValue === null || props.row.rawValue === undefined)
    return "—"
  if (typeof props.row.rawValue === "number")
    return props.row.rawValue.toLocaleString("fr-FR")
  return String(props.row.rawValue)
})

const lineSeries = computed(() => {
  // Affichage générique de l'historique référentiel (pas de détail par-indicateur côté backend MVP).
  const entries = history.entries.value
  return [
    {
      label: props.referentielCode,
      points: entries.map((e) => ({
        x: e.computedAt,
        y: e.scoreGlobal ?? 0,
      })),
    },
  ]
})

const isHistoryEmpty = computed<boolean>(
  () => history.entries.value.length === 0,
)

function onClose(): void {
  emit("close")
}

function onEdit(): void {
  if (editDisabled.value || !props.row) return
  emit("edit", props.row)
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === "Escape") {
    e.preventDefault()
    onClose()
  }
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      try {
        await Promise.resolve(history.load())
      } catch {
        /* error already handled by useScoringHistory */
      }
      await nextTick()
      focusTrap.activate()
    } else {
      focusTrap.deactivate()
    }
  },
  { immediate: true },
)
</script>

<template>
  <div v-if="open" class="indicateur-drawer__root">
    <div class="indicateur-drawer__backdrop" data-testid="indicateur-drawer-backdrop" @click="onClose" />
    <aside
      ref="drawerRef"
      class="indicateur-drawer"
      data-testid="indicateur-drawer"
      role="dialog"
      aria-modal="true"
      :aria-label="t('scoring.indicateur.value')"
      tabindex="-1"
      @keydown="onKeydown"
    >
      <header class="indicateur-drawer__header">
        <h2 class="indicateur-drawer__title" v-if="row">
          {{ row.indicateurCode }}
        </h2>
        <button
          type="button"
          class="indicateur-drawer__close"
          data-testid="indicateur-drawer-close"
          :aria-label="t('scoring.buttons.close')"
          @click="onClose"
        >
          ×
        </button>
      </header>

      <p
        v-if="disableEdit"
        class="indicateur-drawer__snapshot-notice"
        data-testid="indicateur-drawer-snapshot-notice"
        role="status"
      >
        {{ t("scoring.snapshot.drilldownDisabled") }}
      </p>

      <section v-if="row" class="indicateur-drawer__body">
        <dl class="indicateur-drawer__meta">
          <div>
            <dt>{{ t("scoring.indicateur.value") }}</dt>
            <dd
              class="indicateur-drawer__value tabular-nums"
              data-testid="indicateur-drawer-value"
            >
              {{ valueLabel }}
            </dd>
          </div>
          <div v-if="row.weight !== null">
            <dt>{{ t("scoring.indicateur.unit") }}</dt>
            <dd class="tabular-nums">{{ row.weight }}</dd>
          </div>
          <div v-if="row.sourceId">
            <dt>{{ t("scoring.indicateur.sources") }}</dt>
            <dd>
              <RevokedSourceBadge
                v-if="row.isSourceRevoked"
                :source-id="row.sourceId"
              />
              <VizSourcePin v-else :source_id="row.sourceId" />
            </dd>
          </div>
        </dl>

        <div class="indicateur-drawer__chart">
          <h3 class="indicateur-drawer__subtitle">
            {{ t("scoring.indicateur.history") }}
          </h3>
          <VizLineChart
            :series="lineSeries"
            size="sm"
            :loading="history.loading.value"
            :empty="isHistoryEmpty"
            :title="referentielCode"
            data-testid="indicateur-drawer-chart"
          />
        </div>
      </section>

      <footer class="indicateur-drawer__footer">
        <button
          type="button"
          class="indicateur-drawer__btn indicateur-drawer__btn--primary"
          data-testid="indicateur-drawer-edit"
          :disabled="editDisabled"
          :title="
            editDisabled && row && !row.isEditable
              ? t('scoring.errors.notEditableHere')
              : undefined
          "
          @click="onEdit"
        >
          {{ t("scoring.buttons.edit") }}
        </button>
        <button
          type="button"
          class="indicateur-drawer__btn"
          data-testid="indicateur-drawer-close-footer"
          @click="onClose"
        >
          {{ t("scoring.buttons.close") }}
        </button>
      </footer>
    </aside>
  </div>
</template>

<style scoped>
.indicateur-drawer__backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.32);
  z-index: 1040;
}
.indicateur-drawer {
  position: fixed;
  top: 0;
  right: 0;
  height: 100vh;
  width: min(480px, 100vw);
  background: var(--color-surface, #fff);
  box-shadow: -4px 0 16px rgba(0, 0, 0, 0.12);
  z-index: 1050;
  display: flex;
  flex-direction: column;
  outline: none;
}
@media (max-width: 768px) {
  .indicateur-drawer { width: 100vw; }
}
.indicateur-drawer__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4, 1rem);
  border-bottom: 1px solid var(--color-neutral-200, #e5e5e5);
}
.indicateur-drawer__title {
  margin: 0;
  font-family: var(--font-mono);
  font-size: var(--font-size-lg, 1.125rem);
  font-weight: 600;
}
.indicateur-drawer__close {
  font-size: 1.5rem;
  background: transparent;
  border: 0;
  cursor: pointer;
  line-height: 1;
}
.indicateur-drawer__body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4, 1rem);
  display: flex;
  flex-direction: column;
  gap: var(--space-4, 1rem);
}
.indicateur-drawer__meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3, 0.75rem);
  margin: 0;
}
.indicateur-drawer__meta dt {
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-muted, #6b7280);
  margin-bottom: 2px;
}
.indicateur-drawer__meta dd {
  margin: 0;
  font-size: var(--font-size-md, 1rem);
}
.indicateur-drawer__value {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.indicateur-drawer__subtitle {
  font-size: var(--font-size-sm, 0.875rem);
  font-weight: 600;
  margin: 0 0 var(--space-2, 0.5rem) 0;
}
.indicateur-drawer__footer {
  display: flex;
  gap: var(--space-2, 0.5rem);
  padding: var(--space-3, 0.75rem) var(--space-4, 1rem);
  border-top: 1px solid var(--color-neutral-200, #e5e5e5);
}
.indicateur-drawer__btn {
  font-family: inherit;
  padding: var(--space-2, 0.5rem) var(--space-3, 0.75rem);
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--color-neutral-300, #d4d4d4);
  background: var(--color-surface, #fff);
  cursor: pointer;
}
.indicateur-drawer__btn--primary {
  background: var(--color-primary, #3b82f6);
  color: #fff;
  border-color: var(--color-primary, #3b82f6);
}
.indicateur-drawer__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.tabular-nums { font-variant-numeric: tabular-nums; }
.indicateur-drawer__snapshot-notice {
  background: var(--color-warning-50, #fffbeb);
  border: 1px solid var(--color-warning-200, #fde68a);
  color: var(--color-warning-800, #92400e);
  padding: var(--space-2, 0.5rem) var(--space-3, 0.75rem);
  margin: var(--space-3, 0.75rem) var(--space-4, 1rem) 0 var(--space-4, 1rem);
  border-radius: var(--radius-sm, 4px);
  font-size: var(--font-size-sm, 0.875rem);
}
</style>
