<script setup lang="ts">
// F51 T058 — Indicateur d'étape sticky-top accessible.
import type { WizardStepKey } from "~/types/candidatures"

interface Props {
  current: WizardStepKey
  progressionPct: number
}
const props = defineProps<Props>()
const emit = defineEmits<{ (e: "go-to", step: WizardStepKey): void }>()

const STEPS: { key: WizardStepKey; label: string }[] = [
  { key: 1, label: "Offre & projet" },
  { key: 2, label: "Données entreprise" },
  { key: 3, label: "Documents" },
  { key: 4, label: "Réponses libres" },
  { key: 5, label: "Récapitulatif" },
]
</script>

<template>
  <nav
    class="sticky top-0 z-10 border-b border-gray-200 bg-white py-3"
    aria-label="Étapes du wizard"
  >
    <ol class="flex items-center justify-between gap-2 px-4 text-sm">
      <li
        v-for="step in STEPS"
        :key="step.key"
        class="flex flex-1 items-center gap-2"
      >
        <button
          type="button"
          class="flex items-center gap-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          :aria-current="step.key === props.current ? 'step' : undefined"
          @click="emit('go-to', step.key)"
        >
          <span
            class="flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold"
            :class="
              step.key < props.current
                ? 'bg-emerald-600 text-white'
                : step.key === props.current
                ? 'bg-emerald-100 text-emerald-700 ring-2 ring-emerald-500'
                : 'bg-gray-200 text-gray-500'
            "
          >
            {{ step.key < props.current ? "✓" : step.key }}
          </span>
          <span
            class="hidden md:inline"
            :class="
              step.key === props.current ? 'font-semibold' : 'text-gray-600'
            "
            >{{ step.label }}</span
          >
        </button>
      </li>
    </ol>
    <div class="mt-2 h-1 w-full bg-gray-100 px-4">
      <div
        class="h-1 rounded-full bg-emerald-500 transition-all"
        :style="{ width: `${props.progressionPct}%` }"
      />
    </div>
  </nav>
</template>
