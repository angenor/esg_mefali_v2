<script setup lang="ts">
// F43 T045 — Wizard step 4 : budget (MoneyField) + horizon en mois.
import { useT } from "~/composables/useT"
import type { WizardData } from "~/composables/useProjetWizard"
import type { MoneyOut } from "~/stores/entreprise"
import MoneyField from "./MoneyField.vue"

interface Props {
  data: WizardData["step4"]
  errors?: Record<string, string>
}

const props = withDefaults(defineProps<Props>(), { errors: () => ({}) })
const emit = defineEmits<{
  (e: "update:data", v: WizardData["step4"]): void
}>()
const { t } = useT()

function onBudget(v: MoneyOut | null): void {
  emit("update:data", { ...props.data, budget: v })
}

function onHorizon(e: Event): void {
  const raw = (e.target as HTMLInputElement).value
  if (raw === "") {
    emit("update:data", { ...props.data, horizon_mois: null })
    return
  }
  const n = Number(raw)
  if (Number.isFinite(n)) {
    emit("update:data", { ...props.data, horizon_mois: Math.trunc(n) })
  }
}
</script>

<template>
  <div class="wizard-step">
    <div class="wizard-step__field">
      <label>{{ t("profil.projets.wizard.field.budget") }}</label>
      <MoneyField
        :model-value="data.budget"
        :label="t('profil.projets.wizard.field.budget')"
        @update:model-value="onBudget"
      />
    </div>
    <div class="wizard-step__field">
      <label for="wiz-horizon">{{ t("profil.projets.wizard.field.horizon_mois") }}</label>
      <input
        id="wiz-horizon"
        type="number"
        min="1"
        max="240"
        :value="data.horizon_mois ?? ''"
        @input="onHorizon"
      />
    </div>
  </div>
</template>

<style scoped>
.wizard-step {
  display: grid;
  gap: 1rem;
}
.wizard-step__field {
  display: grid;
  gap: 0.25rem;
}
.wizard-step__field label {
  font-size: 0.8125rem;
  color: #475569;
  font-weight: 500;
}
.wizard-step__field input {
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  padding: 0.5rem 0.625rem;
  font: inherit;
}
</style>
