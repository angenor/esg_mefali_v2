<script setup lang="ts">
// F43 T043 — Wizard step 2 : secteur + type_impact (UiSelect).
import { useT } from "~/composables/useT"
import type { WizardData } from "~/composables/useProjetWizard"

interface Props {
  data: WizardData["step2"]
  errors?: Record<string, string>
}

const props = withDefaults(defineProps<Props>(), { errors: () => ({}) })
const emit = defineEmits<{
  (e: "update:data", v: WizardData["step2"]): void
}>()
const { t } = useT()

const SECTEURS: { value: string; label: string }[] = [
  { value: "agroalimentaire", label: "Agroalimentaire" },
  { value: "energie", label: "Énergie" },
  { value: "transport", label: "Transport" },
  { value: "industrie", label: "Industrie" },
  { value: "sante", label: "Santé" },
  { value: "education", label: "Éducation" },
  { value: "fintech", label: "FinTech" },
  { value: "construction", label: "Construction" },
  { value: "autre", label: "Autre" },
]

const TYPES_IMPACT: { value: string; label: string }[] = [
  { value: "mitigation_carbone", label: "Mitigation carbone" },
  { value: "adaptation_climat", label: "Adaptation climat" },
  { value: "biodiversite", label: "Biodiversité" },
  { value: "economie_circulaire", label: "Économie circulaire" },
  { value: "social", label: "Social" },
  { value: "autre", label: "Autre" },
]

function update<K extends keyof WizardData["step2"]>(key: K, value: string): void {
  emit("update:data", { ...props.data, [key]: value })
}
</script>

<template>
  <div class="wizard-step">
    <div class="wizard-step__field">
      <label for="wiz-secteur">{{ t("profil.projets.wizard.field.secteur") }} *</label>
      <select
        id="wiz-secteur"
        :value="data.secteur"
        @change="(e) => update('secteur', (e.target as HTMLSelectElement).value)"
      >
        <option value="" disabled>—</option>
        <option v-for="o in SECTEURS" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
    </div>
    <div class="wizard-step__field">
      <label for="wiz-type-impact">{{ t("profil.projets.wizard.field.type_impact") }} *</label>
      <select
        id="wiz-type-impact"
        :value="data.type_impact"
        @change="(e) => update('type_impact', (e.target as HTMLSelectElement).value)"
      >
        <option value="" disabled>—</option>
        <option v-for="o in TYPES_IMPACT" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
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
.wizard-step__field select {
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  padding: 0.5rem 0.625rem;
  font: inherit;
  background: #fff;
}
.wizard-step__field select:focus {
  outline: 2px solid #15803d;
  outline-offset: 1px;
}
</style>
