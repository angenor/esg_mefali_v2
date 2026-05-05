<script setup lang="ts">
// F47 T044 [US2] — Ligne d'activité (valeur + unité + facteur + pin source).
// Cf. specs/047-empreinte-carbone-ui/contracts/frontend-components.md §EmissionLine.

import { computed } from "vue"
import Decimal from "decimal.js"
import UiBadge from "~/components/ui/UiBadge.vue"
import UiButton from "~/components/ui/UiButton.vue"
import FactorSourcePopover from "~/components/carbone/FactorSourcePopover.vue"
import { useT } from "~/composables/useT"
import type { CarbonBreakdownLine } from "~/types/carbon"

interface Props {
  line: CarbonBreakdownLine
  posteLabel: string
  disableEdit?: boolean
  posteCode?: string
  year?: number
}

const props = withDefaults(defineProps<Props>(), { disableEdit: false })

const emit = defineEmits<{
  edit: [line: CarbonBreakdownLine]
}>()

function onEditClick(): void {
  emit("edit", props.line)
  if (typeof window !== "undefined" && props.posteCode && props.year) {
    window.dispatchEvent(
      new CustomEvent("carbon:edit-line:open", {
        detail: { year: props.year, line: props.line, posteCode: props.posteCode },
      }),
    )
  }
}

const { t } = useT()

const tCo2e = computed(() =>
  new Decimal(props.line.kgco2e).dividedBy(1000).toFixed(3),
)

const sourceMissing = computed(() => !props.line.source_id)
</script>

<template>
  <li
    class="flex flex-wrap items-center gap-3 border-b border-neutral-100 py-2 last:border-b-0"
    :aria-label="`${posteLabel} — ${line.quantity} ${line.unit}`"
  >
    <div class="flex-1 min-w-0">
      <div class="text-sm font-medium text-neutral-900">
        {{ posteLabel }}
      </div>
      <div class="text-xs text-neutral-500 tabular-nums">
        {{ line.quantity }} {{ line.unit }} ×
        {{ line.factor_value }} kgCO₂e/{{ line.unit }}
      </div>
    </div>
    <FactorSourcePopover
      :factor-id="line.factor_id"
      :factor-version="line.factor_version"
      :factor-source-id="line.factor_source_id"
    />
    <div class="text-sm font-semibold tabular-nums text-neutral-900 w-24 text-right">
      {{ tCo2e }} tCO₂e
    </div>
    <UiBadge
      v-if="sourceMissing"
      severity="warning"
      :aria-label="t('carbon.line.sourceMissing')"
    >
      {{ t("carbon.line.sourceMissing") }}
    </UiBadge>
    <UiButton
      variant="ghost"
      size="sm"
      :disabled="disableEdit"
      @click="onEditClick"
    >
      {{ t("carbon.line.modify") }}
    </UiButton>
  </li>
</template>
