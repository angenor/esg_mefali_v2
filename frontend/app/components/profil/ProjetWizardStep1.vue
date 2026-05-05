<script setup lang="ts">
// F43 T042 — Wizard step 1 : nom + description (validation Zod nom min 3 / max 120).
import { useT } from "~/composables/useT"
import type { WizardData } from "~/composables/useProjetWizard"

interface Props {
  data: WizardData["step1"]
  errors?: Record<string, string>
}

const props = withDefaults(defineProps<Props>(), { errors: () => ({}) })
const emit = defineEmits<{
  (e: "update:data", v: WizardData["step1"]): void
}>()

const { t } = useT()

function update<K extends keyof WizardData["step1"]>(key: K, value: WizardData["step1"][K]): void {
  emit("update:data", { ...props.data, [key]: value })
}
</script>

<template>
  <div class="wizard-step">
    <div class="wizard-step__field">
      <label for="wiz-nom">{{ t("profil.projets.wizard.field.nom") }} *</label>
      <input
        id="wiz-nom"
        type="text"
        :value="data.nom"
        :aria-invalid="errors.nom ? true : undefined"
        @input="(e) => update('nom', (e.target as HTMLInputElement).value)"
      />
      <p v-if="errors.nom === 'nom_min'" class="wizard-step__error" role="alert">
        {{ t("profil.projets.wizard.error.nom_min") }}
      </p>
      <p v-else-if="errors.nom === 'nom_max'" class="wizard-step__error" role="alert">
        {{ t("profil.projets.wizard.error.nom_max") }}
      </p>
    </div>
    <div class="wizard-step__field">
      <label for="wiz-desc">{{ t("profil.projets.wizard.field.description") }}</label>
      <textarea
        id="wiz-desc"
        rows="4"
        :value="data.description"
        @input="(e) => update('description', (e.target as HTMLTextAreaElement).value)"
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
.wizard-step__field input,
.wizard-step__field textarea {
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  padding: 0.5rem 0.625rem;
  font: inherit;
}
.wizard-step__field input:focus,
.wizard-step__field textarea:focus {
  outline: 2px solid #15803d;
  outline-offset: 1px;
}
.wizard-step__error {
  color: #b91c1c;
  font-size: 0.8125rem;
}
</style>
