<script setup lang="ts">
// F45 T036 — Bottom sheet d'édition d'une étape (statut + responsable).
//
// Implémenté sur UiModal (P10 : input riche en sheet/modale, pas inline).
import { computed, ref, watch } from "vue"
import { useT } from "~/composables/useT"
import UiModal from "~/components/ui/UiModal.vue"
import type {
  ActionStep,
  ActionStepPatchPayload,
  ResponsibleOption,
  StepStatus,
} from "~/types/actionPlan"

interface Props {
  open: boolean
  step: ActionStep | null
  responsibleOptions: ResponsibleOption[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: "submit", payload: ActionStepPatchPayload): void
  (e: "close"): void
}>()

const { t } = useT()
const STATUSES: StepStatus[] = ["todo", "doing", "done", "postponed"]

const currentStatus = ref<StepStatus>("todo")
const currentResponsible = ref<string | null>(null)

watch(
  () => props.step,
  (s) => {
    if (s) {
      currentStatus.value = s.status
      currentResponsible.value = s.responsible_user_id
    }
  },
  { immediate: true },
)

const dirty = computed<ActionStepPatchPayload | null>(() => {
  if (!props.step) return null
  const patch: ActionStepPatchPayload = {}
  if (currentStatus.value !== props.step.status) patch.status = currentStatus.value
  if (currentResponsible.value !== props.step.responsible_user_id)
    patch.responsible_user_id = currentResponsible.value
  return Object.keys(patch).length ? patch : null
})

function onSubmit(): void {
  if (!dirty.value) return
  emit("submit", dirty.value)
}

function onChangeResponsible(e: Event): void {
  const v = (e.target as HTMLSelectElement).value
  currentResponsible.value = v === "" ? null : v
}
</script>

<template>
  <UiModal
    :model-value="open"
    size="md"
    :aria-label="t('planAction.editSheet.title')"
    @close="emit('close')"
  >
    <template #header>
      <h2>{{ t("planAction.editSheet.title") }}</h2>
    </template>
    <form v-if="step" class="pa-edit" @submit.prevent="onSubmit">
      <fieldset class="pa-edit__group">
        <legend>{{ t("planAction.editSheet.statusLabel") }}</legend>
        <label v-for="s in STATUSES" :key="s" class="pa-edit__option">
          <input
            type="radio"
            name="status"
            :value="s"
            :checked="currentStatus === s"
            @change="currentStatus = s"
          />
          {{ t(`planAction.filters.status.${s}`) }}
        </label>
      </fieldset>
      <label class="pa-edit__group">
        <span>{{ t("planAction.editSheet.responsibleLabel") }}</span>
        <select :value="currentResponsible ?? ''" @change="onChangeResponsible">
          <option value="">{{ t("planAction.editSheet.responsibleNone") }}</option>
          <option v-for="opt in responsibleOptions" :key="opt.id" :value="opt.id">
            {{ opt.label }}
          </option>
        </select>
      </label>
    </form>
    <template #footer>
      <button type="button" @click="emit('close')">
        {{ t("planAction.editSheet.cancel") }}
      </button>
      <button type="button" :disabled="!dirty" @click="onSubmit">
        {{ t("planAction.editSheet.submit") }}
      </button>
    </template>
  </UiModal>
</template>

<style scoped>
.pa-edit { display: flex; flex-direction: column; gap: var(--space-3); }
.pa-edit__group { display: flex; flex-direction: column; gap: var(--space-2); }
.pa-edit__option { display: inline-flex; gap: var(--space-2); }
</style>
