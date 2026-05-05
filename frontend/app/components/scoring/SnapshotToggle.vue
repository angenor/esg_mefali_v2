<script setup lang="ts">
// F46 T087 [US8] — Toggle snapshot intangible (mode lecture seule sur calcul historique).
// Cf. specs/046-scoring-esg-ui/contracts/frontend-components.md §SnapshotToggle.
import { computed, ref, watch } from "vue"
import { useT } from "~/composables/useT"
import type { ScoreHistoryEntryVM } from "~/types/scoring"

interface Props {
  entries: ScoreHistoryEntryVM[]
  active: boolean
  frozenCalculationId?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  frozenCalculationId: null,
})

const emit = defineEmits<{
  (e: "enter", calcId: string): void
  (e: "exit"): void
}>()

const { t } = useT()

const selectedId = ref<string>(props.frozenCalculationId ?? "")

watch(
  () => props.frozenCalculationId,
  (id) => {
    selectedId.value = id ?? ""
  },
)

const fmt = new Intl.DateTimeFormat("fr-FR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
})

const options = computed(() =>
  props.entries.map((e) => ({
    value: e.scoreCalculationId,
    label: t("scoring.snapshot.entryFormat", {
      date: fmt.format(new Date(e.computedAt)),
      score: e.scoreGlobal ?? 0,
      version: e.referentielVersion,
    }),
  })),
)

const activeEntry = computed<ScoreHistoryEntryVM | null>(() => {
  if (!props.active || !props.frozenCalculationId) return null
  return (
    props.entries.find(
      (e) => e.scoreCalculationId === props.frozenCalculationId,
    ) ?? null
  )
})

const bannerLabel = computed<string>(() => {
  const e = activeEntry.value
  if (!e) return ""
  return t("scoring.snapshot.banner", {
    date: fmt.format(new Date(e.computedAt)),
    version: e.referentielVersion,
  })
})

function onToggle(e: Event): void {
  const target = e.target as HTMLInputElement
  if (target.checked) {
    if (!selectedId.value && options.value.length > 0) {
      selectedId.value = options.value[0]!.value
    }
    if (selectedId.value) emit("enter", selectedId.value)
  } else {
    emit("exit")
  }
}

function onSelect(e: Event): void {
  const target = e.target as HTMLSelectElement
  selectedId.value = target.value
  if (props.active && selectedId.value) {
    emit("enter", selectedId.value)
  }
}
</script>

<template>
  <div class="snapshot-toggle" data-testid="snapshot-toggle">
    <div
      v-if="active && activeEntry"
      class="snapshot-toggle__banner"
      data-testid="snapshot-banner"
      role="alert"
    >
      {{ bannerLabel }}
    </div>
    <div class="snapshot-toggle__controls">
      <label class="snapshot-toggle__switch">
        <input
          type="checkbox"
          data-testid="snapshot-switch"
          :checked="active"
          :disabled="entries.length === 0"
          @change="onToggle"
        />
        <span>{{ t("scoring.snapshot.toggleLabel") }}</span>
      </label>
      <select
        v-if="entries.length > 0"
        class="snapshot-toggle__select"
        data-testid="snapshot-select"
        :value="selectedId"
        @change="onSelect"
      >
        <option value="" disabled>
          {{ t("scoring.snapshot.selectPlaceholder") }}
        </option>
        <option v-for="o in options" :key="o.value" :value="o.value">
          {{ o.label }}
        </option>
      </select>
    </div>
  </div>
</template>

<style scoped>
.snapshot-toggle {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 0.5rem);
}
.snapshot-toggle__banner {
  background: var(--color-warning-100, #fef3c7);
  border: 1px solid var(--color-warning-300, #fcd34d);
  color: var(--color-warning-800, #92400e);
  padding: var(--space-3, 0.75rem) var(--space-4, 1rem);
  border-radius: var(--radius-md, 8px);
  font-weight: 500;
}
.snapshot-toggle__controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3, 0.75rem);
}
.snapshot-toggle__switch {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2, 0.5rem);
  font-size: var(--font-size-sm, 0.875rem);
  cursor: pointer;
}
.snapshot-toggle__select {
  padding: var(--space-2, 0.5rem) var(--space-3, 0.75rem);
  border: 1px solid var(--color-neutral-300, #d4d4d4);
  border-radius: var(--radius-md, 8px);
  font-family: inherit;
  font-size: var(--font-size-sm, 0.875rem);
  min-height: 36px;
}
</style>
