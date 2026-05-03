<script setup lang="ts">
import { ref } from 'vue'

definePageMeta({ middleware: ['dev-only'] })

const text = ref('')
const num = ref<number | null>(null)
const sel = ref<string | null>(null)
const radio = ref<string>('a')
const checks = ref<string[]>([])
const switchOn = ref(false)
const sliderVal = ref(50)
const rangeVal = ref<[number, number]>([20, 80])
const dateVal = ref('')
const modalOpen = ref(false)
const popOpen = ref(false)

const opts = [
  { value: 'a', label: 'Option A' },
  { value: 'b', label: 'Option B' },
  { value: 'c', label: 'Option C' },
]
</script>

<template>
  <main class="showcase">
    <h1>UI Primitives — Showcase</h1>

    <UiCard>
      <template #header>UiButton</template>
      <div class="row">
        <UiButton>Primary</UiButton>
        <UiButton variant="secondary">Secondary</UiButton>
        <UiButton variant="ghost">Ghost</UiButton>
        <UiButton variant="danger">Danger</UiButton>
        <UiButton variant="link">Link</UiButton>
        <UiButton :loading="true">Loading</UiButton>
        <UiButton disabled>Disabled</UiButton>
      </div>
    </UiCard>

    <UiCard>
      <template #header>UiInput / UiTextarea / UiNumber</template>
      <div class="grid">
        <UiFormField label="Texte"><template #default="{ id }"><UiInput :id="id" v-model="text" placeholder="Entrer du texte" /></template></UiFormField>
        <UiFormField label="Description"><template #default="{ id }"><UiTextarea :id="id" /></template></UiFormField>
        <UiFormField label="Montant XOF"><template #default="{ id }"><UiNumber :id="id" v-model="num" mode="money" currency="XOF" /></template></UiFormField>
      </div>
    </UiCard>

    <UiCard>
      <template #header>UiSelect / UiCombobox / UiMultiSelect</template>
      <div class="grid">
        <UiFormField label="Select"><template #default="{ id }"><UiSelect :id="id" v-model="sel" :options="opts" /></template></UiFormField>
        <UiFormField label="Combobox"><template #default="{ id }"><UiCombobox :id="id" v-model="sel" :options="opts" /></template></UiFormField>
        <UiFormField label="MultiSelect"><template #default="{ id }"><UiMultiSelect :id="id" :options="opts" /></template></UiFormField>
      </div>
    </UiCard>

    <UiCard>
      <template #header>UiRadioGroup / UiCheckboxGroup / UiSwitch</template>
      <div class="grid">
        <UiFormField label="Régime"><template #default="{ id }"><UiRadioGroup :id="id" v-model="radio" :options="opts" /></template></UiFormField>
        <UiFormField label="Tags"><template #default="{ id }"><UiCheckboxGroup :id="id" v-model="checks" :options="opts" /></template></UiFormField>
        <UiFormField label="Notification"><template #default="{ id }"><UiSwitch :id="id" v-model="switchOn" aria-label="Notifications" /></template></UiFormField>
      </div>
    </UiCard>

    <UiCard>
      <template #header>UiSlider</template>
      <UiSlider v-model="sliderVal" aria-label="Volume" />
      <UiSlider v-model="rangeVal" :range="true" />
    </UiCard>

    <UiCard>
      <template #header>UiDatePicker / UiDateRangePicker</template>
      <div class="grid">
        <UiFormField label="Date"><template #default="{ id }"><UiDatePicker :id="id" v-model="dateVal" /></template></UiFormField>
        <UiFormField label="Plage"><template #default="{ id }"><UiDateRangePicker :id="id" /></template></UiFormField>
      </div>
    </UiCard>

    <UiCard>
      <template #header>UiFileUpload</template>
      <UiFileUpload />
    </UiCard>

    <UiCard>
      <template #header>UiModal / UiPopover / UiTooltip</template>
      <div class="row">
        <UiButton @click="modalOpen = true">Ouvrir modal</UiButton>
        <UiPopover v-model="popOpen">
          <template #trigger><UiButton variant="secondary">Popover</UiButton></template>
          <template #content>Contenu du popover</template>
        </UiPopover>
        <UiTooltip>
          <UiButton variant="ghost" aria-label="Aide">?</UiButton>
          <template #content>Aide contextuelle</template>
        </UiTooltip>
      </div>
      <UiModal v-model="modalOpen">
        <template #header><h2 id="m-h">Titre</h2></template>
        <p>Contenu de la modale.</p>
        <template #footer>
          <UiButton variant="ghost" @click="modalOpen = false">Annuler</UiButton>
          <UiButton @click="modalOpen = false">Valider</UiButton>
        </template>
      </UiModal>
    </UiCard>

    <UiCard>
      <template #header>UiCard / UiBadge / UiTag / UiAvatar</template>
      <div class="row">
        <UiBadge severity="info">Info</UiBadge>
        <UiBadge severity="success">Succès</UiBadge>
        <UiBadge severity="warning" variant="solid">Attention</UiBadge>
        <UiBadge severity="error" variant="solid">Erreur</UiBadge>
        <UiTag>PME</UiTag>
        <UiTag :removable="true" aria-label="Filtre Industrie">Industrie</UiTag>
        <UiAvatar name="Aïssatou Diallo" />
        <UiAvatar name="Jean Dupont" shape="square" size="lg" />
      </div>
    </UiCard>

    <UiCard>
      <template #header>UiEmptyState / UiSkeleton / UiSpinner / UiProgress</template>
      <UiEmptyState title="Aucune donnée" description="Ajoutez votre premier projet" action-label="Créer" />
      <div class="grid">
        <UiSkeleton :lines="3" />
        <UiSkeleton shape="circle" />
        <UiSpinner />
        <UiProgress :model-value="60" />
      </div>
    </UiCard>
  </main>
</template>

<style scoped>
.showcase {
  max-width: 960px;
  margin: var(--space-6) auto;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  font-family: var(--font-sans);
}
.row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  padding: var(--space-3);
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-3);
  padding: var(--space-3);
}
</style>
