<script setup lang="ts">
// F43 T044 — Wizard step 3 : pays mono + région obligatoire + lat/lng optionnels.
import { useT } from "~/composables/useT"
import type { WizardData } from "~/composables/useProjetWizard"
import CountryMultiSelect from "./CountryMultiSelect.vue"

interface Props {
  data: WizardData["step3"]
  errors?: Record<string, string>
}

const props = withDefaults(defineProps<Props>(), { errors: () => ({}) })
const emit = defineEmits<{
  (e: "update:data", v: WizardData["step3"]): void
}>()
const { t } = useT()

function update<K extends keyof WizardData["step3"]>(key: K, value: string): void {
  emit("update:data", { ...props.data, [key]: value })
}

function onCountry(codes: string[]): void {
  update("localisation_pays_iso2", codes[0] ?? "")
}
</script>

<template>
  <div class="wizard-step">
    <div class="wizard-step__field">
      <label>{{ t("profil.projets.wizard.field.localisation_pays_iso2") }} *</label>
      <CountryMultiSelect
        :model-value="data.localisation_pays_iso2 ? [data.localisation_pays_iso2] : []"
        :mono="true"
        :label="t('profil.projets.wizard.field.localisation_pays_iso2')"
        @update:model-value="onCountry"
      />
    </div>
    <div class="wizard-step__field">
      <label for="wiz-region">{{ t("profil.projets.wizard.field.localisation_region") }} *</label>
      <input
        id="wiz-region"
        type="text"
        :value="data.localisation_region"
        @input="(e) => update('localisation_region', (e.target as HTMLInputElement).value)"
      />
    </div>
    <details class="wizard-step__advanced">
      <summary>Coordonnées GPS (optionnelles)</summary>
      <div class="wizard-step__row">
        <div class="wizard-step__field">
          <label for="wiz-lat">{{ t("profil.projets.wizard.field.localisation_lat") }}</label>
          <input
            id="wiz-lat"
            type="text"
            inputmode="decimal"
            :value="data.localisation_lat"
            @input="(e) => update('localisation_lat', (e.target as HTMLInputElement).value)"
          />
        </div>
        <div class="wizard-step__field">
          <label for="wiz-lng">{{ t("profil.projets.wizard.field.localisation_lng") }}</label>
          <input
            id="wiz-lng"
            type="text"
            inputmode="decimal"
            :value="data.localisation_lng"
            @input="(e) => update('localisation_lng', (e.target as HTMLInputElement).value)"
          />
        </div>
      </div>
    </details>
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
.wizard-step__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
.wizard-step__advanced summary {
  cursor: pointer;
  font-size: 0.8125rem;
  color: #15803d;
  margin-bottom: 0.5rem;
}
</style>
