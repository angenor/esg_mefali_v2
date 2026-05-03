<script setup lang="ts">
// F43 T021 — SectionCard : bascule lecture/édition par section, slot fields, émet update:field.
import { computed, nextTick, ref, watch } from "vue"
import { useT } from "~/composables/useT"

export interface FieldDescriptor {
  /** Clé de champ (correspond à la clé renvoyée par l'API). */
  key: string
  /** Label FR. */
  label: string
  /** Type de rendu (input, textarea, select, money, country, country-multi, year, number). */
  kind:
    | "input"
    | "textarea"
    | "select"
    | "money"
    | "country"
    | "country-multi"
    | "year"
    | "number"
  /** Valeur du champ — récupérée depuis `data[key]`. */
  required?: boolean
  /** Pour `kind === 'select'`. */
  options?: { value: string; label: string }[]
}

interface Props {
  title: string
  fields: FieldDescriptor[]
  data: Record<string, unknown>
  saving?: Record<string, boolean>
  errors?: Record<string, string | null>
}

const props = withDefaults(defineProps<Props>(), {
  saving: () => ({}),
  errors: () => ({}),
})
const emit = defineEmits<{
  (e: "update:field", payload: { field: string; value: unknown }): void
  (e: "open-history"): void
  (e: "toggle-edit", editing: boolean): void
}>()

const { t } = useT()
const editing = ref(false)
const cardRef = ref<HTMLElement | null>(null)

function toggleEdit(): void {
  editing.value = !editing.value
  emit("toggle-edit", editing.value)
}

watch(editing, async (isEditing) => {
  if (isEditing) {
    await nextTick()
    const firstInput = cardRef.value?.querySelector<HTMLElement>(
      "input, select, textarea, [tabindex]:not([tabindex='-1'])",
    )
    firstInput?.focus()
  }
})

function onUpdate(field: string, value: unknown): void {
  emit("update:field", { field, value })
}

const isSaving = computed(() => Object.values(props.saving).some(Boolean))
</script>

<template>
  <section ref="cardRef" class="section-card" :data-editing="editing || undefined">
    <header class="section-card__header">
      <h2 class="section-card__title">{{ title }}</h2>
      <div class="section-card__actions">
        <span v-if="isSaving" aria-live="polite" class="section-card__saving">
          {{ t("profil.entreprise.autosave.saving") }}
        </span>
        <button
          type="button"
          class="section-card__btn"
          data-testid="section-history-btn"
          @click="emit('open-history')"
        >
          {{ t("profil.entreprise.action.history") }}
        </button>
        <button
          type="button"
          class="section-card__btn section-card__btn--primary"
          @click="toggleEdit"
        >
          {{ editing
            ? t("profil.entreprise.action.cancel")
            : t("profil.entreprise.action.edit") }}
        </button>
      </div>
    </header>

    <div class="section-card__body">
      <slot
        :editing="editing"
        :on-update="onUpdate"
        :data="data"
        :errors="errors"
        :saving="saving"
      >
        <!-- Fallback : rendu basique des champs en mode lecture. -->
        <dl class="section-card__fields">
          <div v-for="field in fields" :key="field.key" class="section-card__field">
            <dt>{{ field.label }}</dt>
            <dd>{{ data[field.key] ?? "—" }}</dd>
          </div>
        </dl>
      </slot>
    </div>
  </section>
</template>

<style scoped>
.section-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 0.75rem;
  padding: 1rem 1.25rem;
}
.section-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}
.section-card__title {
  font-weight: 600;
  font-size: 1.125rem;
  color: #0f172a;
}
.section-card__actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.section-card__saving {
  font-size: 0.75rem;
  color: #15803d;
}
.section-card__btn {
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  padding: 0.35rem 0.75rem;
  background: #fff;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
}
.section-card__btn--primary {
  background: #15803d;
  color: #fff;
  border-color: #15803d;
}
.section-card__fields {
  display: grid;
  gap: 0.5rem;
}
.section-card__field {
  display: grid;
  grid-template-columns: 12rem 1fr;
  gap: 0.5rem;
  font-size: 0.875rem;
}
.section-card__field dt {
  color: #475569;
  font-weight: 500;
}
.section-card__field dd {
  color: #0f172a;
}
@media (max-width: 640px) {
  .section-card__field {
    grid-template-columns: 1fr;
  }
}
</style>
