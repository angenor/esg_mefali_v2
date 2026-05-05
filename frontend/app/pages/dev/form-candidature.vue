<script setup lang="ts">
import { ref } from 'vue'
import type { UiOption, UiUploadFile } from '~/types/ui'

definePageMeta({ middleware: 'dev-only' })

interface FormState {
  raisonSociale: string
  chiffreAffaires: number | null
  secteur: string | null
  pays: string | null
  dateConstitution: string | null
  documents: UiUploadFile[]
}

const form = ref<FormState>({
  raisonSociale: '',
  chiffreAffaires: null,
  secteur: null,
  pays: null,
  dateConstitution: null,
  documents: [],
})

const secteurs: UiOption<string>[] = [
  { value: 'agro', label: 'Agro-alimentaire' },
  { value: 'industrie', label: 'Industrie' },
  { value: 'services', label: 'Services' },
  { value: 'btp', label: 'BTP' },
  { value: 'commerce', label: 'Commerce' },
]

// 200 pays mockés pour tester virtualisation locale.
const pays: UiOption<string>[] = Array.from({ length: 200 }, (_, i) => ({
  value: `c${i}`,
  label: `Pays ${String(i + 1).padStart(3, '0')}`,
}))

const submitted = ref<FormState | null>(null)
function onSubmit(): void {
  submitted.value = JSON.parse(JSON.stringify(form.value))
}
</script>

<template>
  <main class="page">
    <h1>Démo — Formulaire candidature (F37 atomes uniquement)</h1>
    <form class="form" @submit.prevent="onSubmit">
      <UiFormField label="Raison sociale" required>
        <template #default="b">
          <UiInput v-bind="b" v-model="form.raisonSociale" placeholder="Ex. Acme SARL" />
        </template>
      </UiFormField>

      <UiFormField label="Chiffre d'affaires (XOF)" helper="Annuel HT">
        <template #default="b">
          <UiNumber
            v-bind="b"
            v-model="form.chiffreAffaires"
            mode="money"
            currency="XOF"
            :min="0"
          />
        </template>
      </UiFormField>

      <UiFormField label="Secteur">
        <template #default="b">
          <UiSelect v-bind="b" v-model="form.secteur" :options="secteurs" />
        </template>
      </UiFormField>

      <UiFormField label="Pays" helper="Tape pour rechercher">
        <template #default="b">
          <UiCombobox v-bind="b" v-model="form.pays" :options="pays" />
        </template>
      </UiFormField>

      <UiFormField label="Date de constitution">
        <template #default="b">
          <UiDatePicker v-bind="b" v-model="form.dateConstitution" max="2026-12-31" />
        </template>
      </UiFormField>

      <UiFormField label="Documents (PDF/PNG)">
        <template #default>
          <UiFileUpload
            v-model="form.documents"
            :accept="['application/pdf', 'image/*']"
            :max-size="5 * 1024 * 1024"
          />
        </template>
      </UiFormField>

      <UiButton type="submit" variant="primary">Envoyer</UiButton>
    </form>

    <section v-if="submitted" class="result">
      <h2>Soumission</h2>
      <pre>{{ JSON.stringify(submitted, null, 2) }}</pre>
    </section>
  </main>
</template>

<style scoped>
.page {
  max-width: 720px;
  margin: 0 auto;
  padding: var(--space-6);
  font-family: var(--font-sans);
  color: var(--color-text);
}
.form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  margin-top: var(--space-4);
}
.result {
  margin-top: var(--space-6);
  padding: var(--space-4);
  background: var(--color-neutral-100);
  border-radius: var(--radius-md);
}
pre {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
