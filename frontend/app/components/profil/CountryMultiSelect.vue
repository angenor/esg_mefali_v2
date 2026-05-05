<script setup lang="ts">
// F43 T029 — CountryMultiSelect : sélection multi-pays ISO2 (cluster UEMOA → CEDEAO → monde).
//
// Refuse strictement toute saisie hors `countries-iso2.ts` (R8).
// Recherche par nom FR ou code ISO2.
import { computed, ref, watch } from "vue"
import { COUNTRIES_ISO2 } from "~/data/countries-iso2"
import { useFieldId } from "~/composables/useFieldId"

interface Props {
  modelValue?: string[]
  /** Si true, n'autorise qu'une seule sélection (utilisé par wizard step3). */
  mono?: boolean
  max?: number
  disabled?: boolean
  error?: string
  id?: string
  label?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  mono: false,
  max: undefined,
  disabled: false,
  error: undefined,
  id: undefined,
  label: "",
})

const emit = defineEmits<{
  (e: "update:modelValue", v: string[]): void
}>()

const localId = props.id ?? useFieldId("ui-country")
const errorId = `${localId}-err`
const search = ref("")
const open = ref(false)

const COUNTRY_BY_CODE = computed(() => {
  const map = new Map<string, { code: string; name: string }>()
  for (const c of COUNTRIES_ISO2) map.set(c.code, c)
  return map
})

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return COUNTRIES_ISO2.filter((c) => !props.modelValue.includes(c.code)).filter((c) => {
    if (!q) return true
    return c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q)
  })
})

const selected = computed(() =>
  props.modelValue.map((code) => COUNTRY_BY_CODE.value.get(code) ?? { code, name: code }),
)

function add(code: string): void {
  if (!COUNTRY_BY_CODE.value.has(code)) return
  if (props.modelValue.includes(code)) return
  if (props.mono) {
    emit("update:modelValue", [code])
    search.value = ""
    return
  }
  if (props.max !== undefined && props.modelValue.length >= props.max) return
  emit("update:modelValue", [...props.modelValue, code])
  search.value = ""
}

function remove(code: string): void {
  emit("update:modelValue", props.modelValue.filter((c) => c !== code))
}

function onBlurDelayed(): void {
  setTimeout(() => {
    open.value = false
  }, 120)
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === "Backspace" && search.value === "" && props.modelValue.length > 0) {
    const last = props.modelValue[props.modelValue.length - 1]
    if (last) remove(last)
    e.preventDefault()
  } else if (e.key === "Enter") {
    if (filtered.value.length > 0) {
      add(filtered.value[0]!.code)
      e.preventDefault()
    }
  }
}

watch(
  () => props.modelValue,
  () => {
    /* watcher to ensure reactivity when parent overrides */
  },
)
</script>

<template>
  <div class="country-multi" :data-error="!!error || undefined">
    <div class="country-multi__field" :id="localId">
      <span
        v-for="opt in selected"
        :key="opt.code"
        class="country-multi__chip"
      >
        <span aria-hidden="true">{{ opt.code }}</span>
        <span class="sr-only">{{ opt.name }}</span>
        <span>{{ opt.name }}</span>
        <button
          type="button"
          class="country-multi__remove"
          :aria-label="`Retirer ${opt.name}`"
          @click="remove(opt.code)"
        >
          ×
        </button>
      </span>
      <input
        v-model="search"
        type="text"
        class="country-multi__input"
        :disabled="disabled"
        :aria-invalid="!!error || undefined"
        :aria-describedby="error ? errorId : undefined"
        :aria-label="label || 'Rechercher un pays'"
        :placeholder="modelValue.length === 0 ? 'Tapez un pays…' : ''"
        @focus="open = true"
        @blur="onBlurDelayed"
        @keydown="onKeydown"
      />
    </div>
    <ul
      v-if="open && filtered.length"
      role="listbox"
      class="country-multi__list"
    >
      <li
        v-for="c in filtered.slice(0, 20)"
        :key="c.code"
        role="option"
        :aria-selected="false"
        class="country-multi__option"
        :data-cluster="c.cluster"
        @mousedown.prevent="add(c.code)"
      >
        <strong>{{ c.code }}</strong>
        <span>{{ c.name }}</span>
        <span v-if="c.cluster === 'uemoa'" class="country-multi__badge">UEMOA</span>
        <span v-else-if="c.cluster === 'cedeao'" class="country-multi__badge country-multi__badge--cedeao">CEDEAO</span>
      </li>
    </ul>
    <p v-if="error" :id="errorId" class="country-multi__error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.country-multi {
  position: relative;
  display: grid;
  gap: 0.25rem;
}
.country-multi__field {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  padding: 0.4rem 0.5rem;
  background: #fff;
  min-height: 44px;
  align-items: center;
}
.country-multi[data-error] .country-multi__field {
  border-color: #dc2626;
}
.country-multi__field:focus-within {
  outline: 2px solid #15803d;
  outline-offset: 1px;
}
.country-multi__chip {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.125rem 0.5rem;
  background: #ecfdf5;
  color: #15803d;
  border-radius: 9999px;
  font-size: 0.8125rem;
}
.country-multi__remove {
  background: none;
  border: 0;
  cursor: pointer;
  color: inherit;
  font-size: 1rem;
  line-height: 1;
}
.country-multi__input {
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  font: inherit;
  min-width: 8rem;
}
.country-multi__list {
  position: absolute;
  z-index: 50;
  top: 100%;
  left: 0;
  right: 0;
  margin: 0.25rem 0 0;
  padding: 0;
  list-style: none;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  background: #fff;
  box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.15);
  max-height: 14rem;
  overflow-y: auto;
}
.country-multi__option {
  display: grid;
  grid-template-columns: 2.5rem 1fr auto;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  font-size: 0.875rem;
}
.country-multi__option:hover {
  background: #f1f5f9;
}
.country-multi__option strong {
  color: #475569;
  font-weight: 600;
  font-size: 0.75rem;
}
.country-multi__badge {
  font-size: 0.6875rem;
  background: #fef3c7;
  color: #92400e;
  padding: 0.125rem 0.375rem;
  border-radius: 9999px;
  font-weight: 600;
}
.country-multi__badge--cedeao {
  background: #dbeafe;
  color: #1e40af;
}
.country-multi__error {
  color: #b91c1c;
  font-size: 0.8125rem;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
