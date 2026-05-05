<script setup lang="ts">
// F47 T068 [US5] — Bandeau de recalcul global manuel.
//
// Affiche `Dernier calcul : {date}` formaté FR + bouton `Recalculer` avec
// spinner pendant l'exécution. prefers-reduced-motion → spinner statique.
//
// Cf. specs/047-empreinte-carbone-ui/spec.md US5.

import { computed } from "vue"
import UiButton from "~/components/ui/UiButton.vue"
import UiSpinner from "~/components/ui/UiSpinner.vue"
import { useT } from "~/composables/useT"
import { useReducedMotion } from "~/composables/useReducedMotion"

interface Props {
  year: number
  lastComputedAt: string | null
  loading: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{ recompute: [] }>()

const { t } = useT()
const reducedMotion = useReducedMotion()

const formatted = computed(() => {
  if (!props.lastComputedAt) return null
  try {
    const d = new Date(props.lastComputedAt)
    return new Intl.DateTimeFormat("fr-FR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(d)
  } catch {
    return null
  }
})

function onClick(): void {
  if (props.loading) return
  emit("recompute")
}
</script>

<template>
  <div
    class="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-white px-4 py-3 shadow-sm border border-neutral-200"
    :data-year="year"
  >
    <div class="text-sm text-neutral-600">
      <template v-if="formatted">
        {{ t("carbon.recalc.lastComputed", { date: formatted }) }}
      </template>
      <template v-else>—</template>
    </div>
    <div class="flex items-center gap-2">
      <span
        v-if="loading"
        class="text-xs text-neutral-500"
        aria-live="polite"
      >
        {{ t("carbon.recalc.running") }}
      </span>
      <UiButton
        variant="primary"
        size="sm"
        :disabled="loading"
        :aria-disabled="loading"
        @click="onClick"
      >
        <UiSpinner
          v-if="loading"
          size="sm"
          :data-reduced-motion="reducedMotion ? 'true' : 'false'"
          class="mr-2"
        />
        {{ t("carbon.recalc.button") }}
      </UiButton>
    </div>
  </div>
</template>
