<script setup lang="ts">
import { ref } from 'vue'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'

definePageMeta({ middleware: ['dev-only'] })

const schema = z.object({
  ca: z.number({ invalid_type_error: 'Chiffre d\'affaires requis' }).min(0, 'Doit être positif'),
  currency: z.enum(['XOF', 'EUR', 'USD']),
  regime: z.enum(['reel', 'simplifie', 'forfaitaire']),
})

const { handleSubmit, errors, defineField, resetForm } = useForm({
  validationSchema: toTypedSchema(schema),
  initialValues: { ca: null as unknown as number, currency: 'XOF', regime: 'reel' },
})

const [ca, caAttrs] = defineField('ca')
const [currency, currencyAttrs] = defineField('currency')
const [regime, regimeAttrs] = defineField('regime')

const submitting = ref(false)
const submittedPayload = ref<unknown>(null)

const onSubmit = handleSubmit(async (values) => {
  submitting.value = true
  await new Promise((r) => setTimeout(r, 200))
  submittedPayload.value = values
  submitting.value = false
})

const currencyOptions = [
  { value: 'XOF', label: 'FCFA (XOF)' },
  { value: 'EUR', label: 'Euro (EUR)' },
  { value: 'USD', label: 'Dollar US (USD)' },
]

const regimeOptions = [
  { value: 'reel', label: 'Régime du réel' },
  { value: 'simplifie', label: 'Régime simplifié' },
  { value: 'forfaitaire', label: 'Régime forfaitaire' },
]
</script>

<template>
  <section class="sheet-ca" aria-labelledby="sheet-ca-title">
    <h1 id="sheet-ca-title">Renseigner votre chiffre d'affaires</h1>

    <form @submit.prevent="onSubmit">
      <UiFormField label="Chiffre d'affaires annuel" :helper="'Montant net hors taxes'" required>
        <template #default="{ id }">
          <UiNumber
            :id="id"
            v-model="ca"
            v-bind="caAttrs"
            mode="money"
            :currency="currency || 'XOF'"
            :error="errors.ca"
            :min="0"
          />
        </template>
      </UiFormField>

      <UiFormField label="Devise" required>
        <template #default="{ id }">
          <UiSelect
            :id="id"
            v-model="currency"
            v-bind="currencyAttrs"
            :options="currencyOptions"
            :error="errors.currency"
          />
        </template>
      </UiFormField>

      <UiFormField label="Régime fiscal" required>
        <template #default="{ id }">
          <UiRadioGroup
            :id="id"
            v-model="regime"
            v-bind="regimeAttrs"
            :options="regimeOptions"
            layout="stacked"
            :aria-label="'Régime fiscal'"
          />
        </template>
      </UiFormField>

      <span v-if="errors.regime" class="error" role="alert">{{ errors.regime }}</span>

      <div class="actions">
        <UiButton type="button" variant="ghost" @click="resetForm()">Réinitialiser</UiButton>
        <UiButton type="submit" :loading="submitting">Enregistrer</UiButton>
      </div>
    </form>

    <pre v-if="submittedPayload" class="result" data-testid="result">{{ JSON.stringify(submittedPayload, null, 2) }}</pre>
  </section>
</template>

<style scoped>
.sheet-ca {
  max-width: 560px;
  margin: var(--space-6) auto;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  font-family: var(--font-sans);
}
.sheet-ca form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.actions {
  display: flex;
  gap: var(--space-3);
  justify-content: flex-end;
}
.error {
  color: var(--color-danger-700);
  font-size: var(--font-size-xs);
}
.result {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
}
</style>
