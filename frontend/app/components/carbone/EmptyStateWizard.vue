<script setup lang="ts">
// F47 T076 [US6] — Wizard onboarding 3 étapes (énergie / mobilité / achats).
//
// Affiché tant que `currentFootprint===null`. Hydrate le brouillon localStorage
// au mount, persiste à chaque saisie. Bouton `Répondre librement` (P10).

import { computed, onMounted } from "vue"
import UiButton from "~/components/ui/UiButton.vue"
import UiCard from "~/components/ui/UiCard.vue"
import UiNumber from "~/components/ui/UiNumber.vue"
import UiInput from "~/components/ui/UiInput.vue"
import UiSelect from "~/components/ui/UiSelect.vue"
import UiProgress from "~/components/ui/UiProgress.vue"
import { useCarbonWizard, type WizardStepKey } from "~/composables/useCarbonWizard"
import { useT } from "~/composables/useT"

interface Props {
  year: number
}

const props = defineProps<Props>()

const { t } = useT()
const wizard = useCarbonWizard()

onMounted(() => {
  wizard.hydrate(null)
})

const isStarted = computed(() => wizard.draft.value !== null)

const STEP_DEFS: Array<{
  key: WizardStepKey
  units: string[]
  iconLabel: string
}> = [
  { key: "energy", units: ["kWh", "MJ"], iconLabel: "⚡" },
  { key: "mobility", units: ["km", "litre"], iconLabel: "🚗" },
  { key: "purchases", units: ["EUR", "FCFA"], iconLabel: "🛒" },
]

function stepLabel(key: WizardStepKey): string {
  return t(`carbon.wizard.steps.${key}`)
}

function unitOptions(key: WizardStepKey) {
  const def = STEP_DEFS.find((d) => d.key === key)!
  return def.units.map((u) => ({ value: u, label: u }))
}

function start(): void {
  wizard.start(props.year, null)
}

function answer(key: WizardStepKey) {
  const draft = wizard.draft.value
  return draft?.answers[key] ?? { quantity: "", unit: STEP_DEFS.find((d) => d.key === key)!.units[0]!, source_id: "" }
}

function update(
  key: WizardStepKey,
  field: "quantity" | "unit" | "source_id",
  value: string,
): void {
  const current = answer(key)
  // Type stays the same per step; cast permitted because schemas validate at boundary.
  const next = { ...current, [field]: value } as never
  wizard.setAnswer(key, next)
}

function next(): void {
  wizard.nextStep()
}
function prev(): void {
  wizard.previousStep()
}
async function submit(): Promise<void> {
  await wizard.submit(null)
}
async function freeText(): Promise<void> {
  await wizard.freeText()
}

const currentKey = computed<WizardStepKey>(() => wizard.stepKey.value)
const progress = computed(() => Math.round((wizard.step.value / 3) * 100))
</script>

<template>
  <section
    class="rounded-2xl bg-white p-8 shadow-sm border border-neutral-200"
    :aria-labelledby="'carbon-wizard-title'"
  >
    <header class="mb-4 text-center">
      <h2 id="carbon-wizard-title" class="text-2xl font-bold text-neutral-900">
        {{ t("carbon.wizard.title") }}
      </h2>
      <p class="text-neutral-600 mt-1">{{ t("carbon.wizard.subtitle") }}</p>
    </header>

    <div v-if="!isStarted" class="grid gap-4 md:grid-cols-3">
      <UiCard
        v-for="def in STEP_DEFS"
        :key="def.key"
        class="p-6 text-center"
      >
        <div class="text-3xl mb-2" aria-hidden="true">{{ def.iconLabel }}</div>
        <div class="text-sm font-semibold text-neutral-800">
          {{ stepLabel(def.key) }}
        </div>
      </UiCard>
      <div class="md:col-span-3 mt-4 flex items-center justify-center gap-3">
        <UiButton variant="primary" size="lg" @click="start">
          {{ t("carbon.wizard.start") }}
        </UiButton>
        <UiButton variant="ghost" size="md" @click="freeText">
          {{ t("carbon.wizard.answerFreely") }}
        </UiButton>
      </div>
    </div>

    <div v-else class="space-y-6">
      <div>
        <UiProgress :model-value="progress" />
        <div class="text-xs text-neutral-500 mt-1 text-center">
          {{ t("carbon.wizard.progress", { current: wizard.step.value, total: 3 }) }}
          — {{ stepLabel(currentKey) }}
        </div>
      </div>

      <div
        v-for="def in STEP_DEFS"
        :key="def.key"
        v-show="def.key === currentKey"
        class="grid gap-3 md:grid-cols-3"
      >
        <label class="block">
          <span class="text-sm font-medium text-neutral-700">
            {{ t("carbon.editLine.quantity") }}
          </span>
          <UiNumber
            :model-value="Number(answer(def.key).quantity) || 0"
            @update:model-value="(v) => update(def.key, 'quantity', String(v))"
          />
        </label>
        <label class="block">
          <span class="text-sm font-medium text-neutral-700">
            {{ t("carbon.editLine.unit") }}
          </span>
          <UiSelect
            :model-value="answer(def.key).unit"
            :options="unitOptions(def.key)"
            @update:model-value="(v) => update(def.key, 'unit', String(v))"
          />
        </label>
        <label class="block">
          <span class="text-sm font-medium text-neutral-700">
            {{ t("carbon.editLine.source") }}
          </span>
          <UiInput
            :model-value="answer(def.key).source_id"
            type="text"
            :placeholder="t('carbon.editLine.sourcePlaceholder')"
            @update:model-value="(v) => update(def.key, 'source_id', String(v))"
          />
        </label>
      </div>

      <p class="text-xs text-neutral-400 italic text-center">
        {{ t("carbon.wizard.partialSaved") }}
      </p>

      <div class="flex flex-wrap items-center justify-between gap-3">
        <UiButton
          variant="ghost"
          size="md"
          :disabled="wizard.step.value === 1"
          @click="prev"
        >
          {{ t("carbon.wizard.previous") }}
        </UiButton>
        <UiButton variant="ghost" size="sm" @click="freeText">
          {{ t("carbon.wizard.answerFreely") }}
        </UiButton>
        <UiButton
          v-if="wizard.step.value < 3"
          variant="primary"
          size="md"
          @click="next"
        >
          {{ t("carbon.wizard.next") }}
        </UiButton>
        <UiButton
          v-else
          variant="primary"
          size="md"
          :disabled="wizard.isSubmitting.value"
          @click="submit"
        >
          {{ t("carbon.wizard.finish") }}
        </UiButton>
      </div>
    </div>
  </section>
</template>
