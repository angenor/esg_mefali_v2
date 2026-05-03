<script setup lang="ts">
// F43 T022 — SectionEditor : orchestre les inputs en mode édition d'une SectionCard.
//
// Renvoie un événement `update:field` à chaque saisie (debouncé en amont par
// `useEntrepriseProfile`). Gère `aria-describedby` pour les erreurs.
import { computed } from "vue"
import { useFieldId } from "~/composables/useFieldId"
import type { FieldDescriptor } from "./SectionCard.vue"

interface Props {
  fields: FieldDescriptor[]
  data: Record<string, unknown>
  errors?: Record<string, string | null>
  saving?: Record<string, boolean>
}

const props = withDefaults(defineProps<Props>(), {
  errors: () => ({}),
  saving: () => ({}),
})

const emit = defineEmits<{
  (e: "update:field", payload: { field: string; value: unknown }): void
}>()

interface BoundField {
  key: string
  id: string
  errorId: string
  descriptor: FieldDescriptor
}

const bound = computed<BoundField[]>(() =>
  props.fields.map((d) => {
    const id = useFieldId(`profil-${d.key}`)
    return { key: d.key, descriptor: d, id, errorId: `${id}-err` }
  }),
)

function handleInput(field: string, ev: Event): void {
  const target = ev.target as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
  emit("update:field", { field, value: target.value })
}

function handleNumber(field: string, ev: Event): void {
  const target = ev.target as HTMLInputElement
  const raw = target.value
  if (raw === "") {
    emit("update:field", { field, value: null })
    return
  }
  const n = Number(raw)
  if (Number.isFinite(n)) {
    emit("update:field", { field, value: Math.trunc(n) })
  }
}
</script>

<template>
  <div class="section-editor">
    <div v-for="f in bound" :key="f.key" class="section-editor__row">
      <label :for="f.id" class="section-editor__label">
        {{ f.descriptor.label }}
        <span v-if="f.descriptor.required" aria-hidden="true">*</span>
      </label>
      <div class="section-editor__control">
        <slot
          :name="f.key"
          :id="f.id"
          :value="data[f.key]"
          :on-update="(value: unknown) => emit('update:field', { field: f.key, value })"
        >
          <textarea
            v-if="f.descriptor.kind === 'textarea'"
            :id="f.id"
            :value="(data[f.key] as string | null) ?? ''"
            :aria-invalid="errors[f.key] ? true : undefined"
            :aria-describedby="errors[f.key] ? f.errorId : undefined"
            rows="3"
            @input="(e) => handleInput(f.key, e)"
          />
          <select
            v-else-if="f.descriptor.kind === 'select'"
            :id="f.id"
            :value="(data[f.key] as string | null) ?? ''"
            :aria-invalid="errors[f.key] ? true : undefined"
            :aria-describedby="errors[f.key] ? f.errorId : undefined"
            @change="(e) => handleInput(f.key, e)"
          >
            <option value="" disabled>—</option>
            <option
              v-for="opt in f.descriptor.options ?? []"
              :key="opt.value"
              :value="opt.value"
            >
              {{ opt.label }}
            </option>
          </select>
          <input
            v-else-if="f.descriptor.kind === 'number' || f.descriptor.kind === 'year'"
            :id="f.id"
            type="number"
            :value="(data[f.key] as number | null) ?? ''"
            :aria-invalid="errors[f.key] ? true : undefined"
            :aria-describedby="errors[f.key] ? f.errorId : undefined"
            @input="(e) => handleNumber(f.key, e)"
          />
          <input
            v-else
            :id="f.id"
            type="text"
            :value="(data[f.key] as string | null) ?? ''"
            :aria-invalid="errors[f.key] ? true : undefined"
            :aria-describedby="errors[f.key] ? f.errorId : undefined"
            @input="(e) => handleInput(f.key, e)"
          />
        </slot>
        <p v-if="errors[f.key]" :id="f.errorId" role="alert" class="section-editor__error">
          {{ errors[f.key] }}
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.section-editor {
  display: grid;
  gap: 0.75rem;
}
.section-editor__row {
  display: grid;
  grid-template-columns: 12rem 1fr;
  gap: 0.5rem;
  align-items: start;
}
.section-editor__label {
  color: #475569;
  font-size: 0.875rem;
  padding-top: 0.45rem;
  font-weight: 500;
}
.section-editor__control input,
.section-editor__control select,
.section-editor__control textarea {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  padding: 0.45rem 0.625rem;
  font: inherit;
  background: #fff;
  color: #0f172a;
}
.section-editor__control input:focus,
.section-editor__control select:focus,
.section-editor__control textarea:focus {
  outline: 2px solid #15803d;
  outline-offset: 1px;
}
.section-editor__error {
  color: #b91c1c;
  font-size: 0.8125rem;
  margin-top: 0.25rem;
}
@media (max-width: 640px) {
  .section-editor__row {
    grid-template-columns: 1fr;
  }
}
</style>
