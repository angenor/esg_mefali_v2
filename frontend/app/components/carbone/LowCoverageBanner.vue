<script setup lang="ts">
// F47 T036 [US1] — Bannière d'avertissement couverture < 60 %.
// Cf. specs/047-empreinte-carbone-ui/contracts/frontend-components.md §LowCoverageBanner.

import { computed } from "vue"
import UiButton from "~/components/ui/UiButton.vue"
import { useT } from "~/composables/useT"
import type { CoverageSnapshot } from "~/lib/computeCarbonCoverage"

interface Props {
  coverage: CoverageSnapshot | null
}

const props = defineProps<Props>()

const emit = defineEmits<{ complete: [] }>()

const { t } = useT()

const visible = computed(() => Boolean(props.coverage?.isLow))
const pctRounded = computed(() => Math.round(props.coverage?.globalPct ?? 0))
</script>

<template>
  <div
    v-if="visible"
    class="rounded-xl border border-amber-300 bg-amber-50 p-4 flex items-start gap-4"
    role="status"
    :aria-label="t('carbon.coverageBanner.title')"
  >
    <span aria-hidden="true" class="text-2xl">⚠️</span>
    <div class="flex-1">
      <h4 class="font-semibold text-amber-900">
        {{ t("carbon.coverageBanner.title") }}
      </h4>
      <p class="text-sm text-amber-800 mt-1">
        {{ t("carbon.coverageBanner.description", { pct: pctRounded }) }}
      </p>
    </div>
    <UiButton variant="secondary" size="sm" @click="emit('complete')">
      {{ t("carbon.coverageBanner.cta") }}
    </UiButton>
  </div>
</template>
