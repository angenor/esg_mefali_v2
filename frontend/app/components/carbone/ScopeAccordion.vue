<script setup lang="ts">
// F47 T045 [US2] — Accordéon par scope (header + liste de postes + lignes).
// Cf. specs/047-empreinte-carbone-ui/contracts/frontend-components.md §ScopeAccordion.

import { computed, ref } from "vue"
import Decimal from "decimal.js"
import EmissionLine from "~/components/carbone/EmissionLine.vue"
import UiBadge from "~/components/ui/UiBadge.vue"
import UiButton from "~/components/ui/UiButton.vue"
import UiTooltip from "~/components/ui/UiTooltip.vue"
import { useT } from "~/composables/useT"
import type { Scope } from "~/types/carbon"
import type { ScopeBreakdown } from "~/lib/groupCarbonByScope"

interface Props {
  scope: Scope
  breakdown: ScopeBreakdown | null
  year?: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  edit: [posteCode: string, lineCode: string]
  add: [posteCode: string]
}>()

const { t } = useT()

const open = ref(true)

const scopeLabel = computed(() => t(`carbon.scopes.${props.scope}`))
const scopeShort = computed(() => t(`carbon.scopes.short.${props.scope}`))

const totalTco2e = computed(() =>
  props.breakdown
    ? new Decimal(props.breakdown.totalKgCo2e).dividedBy(1000).toFixed(3)
    : "0.000",
)

const filledRatio = computed(() =>
  props.breakdown
    ? `${props.breakdown.filledPostesCount}/${props.breakdown.expectedPostesCount}`
    : "0/0",
)

const isScope2 = computed(() => props.scope === "2")

function onAddClick(posteCode: string): void {
  emit("add", posteCode)
  if (typeof window !== "undefined" && props.year) {
    window.dispatchEvent(
      new CustomEvent("carbon:edit-line:open", {
        detail: { year: props.year, line: null, posteCode },
      }),
    )
  }
}
</script>

<template>
  <details
    :open="open"
    class="rounded-2xl bg-white shadow-sm border border-neutral-200"
    @toggle="(e) => (open = (e.target as HTMLDetailsElement).open)"
  >
    <summary
      class="flex flex-wrap items-center gap-3 cursor-pointer px-6 py-4 list-none"
      :aria-label="`${scopeLabel} — ${totalTco2e} tCO₂e`"
    >
      <span class="font-semibold text-neutral-900 flex-1">
        {{ scopeLabel }}
      </span>
      <UiBadge severity="info">{{ filledRatio }}</UiBadge>
      <span class="text-sm font-medium tabular-nums text-neutral-700 w-32 text-right">
        {{ totalTco2e }} tCO₂e
      </span>
      <UiTooltip v-if="isScope2">
        <span class="text-xs text-neutral-500 underline cursor-help">
          {{ t("carbon.marketVsLocationBased") }}
        </span>
        <template #content>
          {{ t("carbon.marketVsLocationBasedDetail") }}
        </template>
      </UiTooltip>
    </summary>

    <div v-if="breakdown" class="px-6 pb-4 space-y-4">
      <div
        v-for="group in breakdown.groups"
        :key="group.posteCode"
        class="rounded-lg bg-neutral-50 px-4 py-3"
      >
        <div class="flex items-center justify-between mb-2">
          <h4 class="text-sm font-semibold text-neutral-800">
            {{ t(`carbon.posts.${group.posteCode}` as never) }}
          </h4>
          <UiButton
            v-if="group.lines.length === 0"
            variant="ghost"
            size="sm"
            @click="onAddClick(group.posteCode)"
          >
            {{ t("carbon.line.add") }}
          </UiButton>
        </div>
        <ul v-if="group.lines.length > 0" class="divide-y divide-neutral-100">
          <EmissionLine
            v-for="line in group.lines"
            :key="line.code"
            :line="line"
            :poste-label="t(`carbon.posts.${group.posteCode}` as never)"
            :poste-code="group.posteCode"
            :year="props.year"
            @edit="(l) => emit('edit', group.posteCode, l.code)"
          />
        </ul>
        <p v-else class="text-xs text-neutral-400 italic">
          {{ t("carbon.posteEmpty.label") }}
        </p>
      </div>
    </div>
  </details>
</template>
