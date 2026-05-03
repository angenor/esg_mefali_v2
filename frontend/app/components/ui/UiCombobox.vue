<script setup lang="ts" generic="V extends string | number">
import { computed, nextTick, ref, watch } from 'vue'
import type { UiOption, UiOptionsLoader, UiSize } from '~/types/ui'
import { useFieldId } from '~/composables/useFieldId'
import { useFloating } from '~/composables/useFloating'

interface Props {
  modelValue?: V | null
  options?: UiOption<V>[]
  loader?: UiOptionsLoader<V>
  pageSize?: number
  placeholder?: string
  clearable?: boolean
  creatable?: boolean
  disabled?: boolean
  size?: UiSize
  error?: string
  helper?: string
  id?: string
  ariaLabel?: string
  emptyText?: string
  itemHeight?: number
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  options: () => [],
  loader: undefined,
  pageSize: 20,
  placeholder: 'Sélectionner…',
  clearable: true,
  creatable: false,
  disabled: false,
  size: 'md',
  error: undefined,
  helper: undefined,
  id: undefined,
  ariaLabel: undefined,
  emptyText: 'Aucun résultat',
  itemHeight: 36,
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: V | null): void
  (e: 'select', opt: UiOption<V>): void
  (e: 'reach-end'): void
  (e: 'search', q: string): void
}>()

const open = ref(false)
const search = ref('')
const activeIndex = ref(-1)
const loadedItems = ref<UiOption<V>[]>([])
const page = ref(1)
const totalAsync = ref<number | null>(null)
const loading = ref(false)

const localId = props.id ?? useFieldId('ui-combobox')
const listboxId = `${localId}-listbox`

const floating = useFloating({ placement: 'bottom-start', open })

const items = computed<UiOption<V>[]>(() => {
  if (props.loader) return loadedItems.value
  const q = search.value.toLowerCase()
  if (!q) return props.options
  return props.options.filter((o) => o.label.toLowerCase().includes(q))
})

const virtualize = computed(() => !props.loader && items.value.length > 100)
const visibleStart = ref(0)
const visibleCount = 20

const visibleItems = computed(() => {
  if (!virtualize.value) return items.value.map((o, i) => ({ option: o, index: i }))
  const start = Math.max(0, visibleStart.value)
  return items.value.slice(start, start + visibleCount).map((o, i) => ({ option: o, index: start + i }))
})

const selectedLabel = computed(() => {
  const all = props.loader ? loadedItems.value : props.options
  return all.find((o) => o.value === props.modelValue)?.label ?? ''
})

watch(open, (v) => {
  if (v) {
    nextTick(() => (activeIndex.value = items.value.findIndex((o) => o.value === props.modelValue)))
    if (props.loader && loadedItems.value.length === 0) {
      fetchPage(true)
    }
  }
})

async function fetchPage(reset = false): Promise<void> {
  if (!props.loader) return
  loading.value = true
  try {
    if (reset) {
      page.value = 1
      loadedItems.value = []
    }
    const r = await props.loader({ search: search.value, page: page.value, pageSize: props.pageSize })
    loadedItems.value = reset ? r.items : [...loadedItems.value, ...r.items]
    totalAsync.value = r.total
  } finally {
    loading.value = false
  }
}

watch(search, () => {
  emit('search', search.value)
  if (props.loader) fetchPage(true)
})

function selectOption(opt: UiOption<V>): void {
  if (opt.disabled) return
  emit('update:modelValue', opt.value)
  emit('select', opt)
  open.value = false
  search.value = ''
}

function selectByIndex(i: number): void {
  const it = items.value[i]
  if (it) selectOption(it)
}

function onListScroll(e: Event): void {
  const el = e.target as HTMLElement
  if (virtualize.value) {
    visibleStart.value = Math.floor(el.scrollTop / props.itemHeight)
  }
  if (props.loader && el.scrollTop + el.clientHeight >= el.scrollHeight - 4) {
    if (totalAsync.value !== null && loadedItems.value.length >= totalAsync.value) return
    page.value += 1
    emit('reach-end')
    fetchPage()
  }
}

function onKeydown(e: KeyboardEvent): void {
  if (!open.value && (e.key === 'ArrowDown' || e.key === 'Enter')) {
    open.value = true
    e.preventDefault()
    return
  }
  if (!open.value) return
  if (e.key === 'ArrowDown') {
    activeIndex.value = Math.min(items.value.length - 1, activeIndex.value + 1)
    e.preventDefault()
  } else if (e.key === 'ArrowUp') {
    activeIndex.value = Math.max(0, activeIndex.value - 1)
    e.preventDefault()
  } else if (e.key === 'Enter') {
    if (activeIndex.value >= 0) selectByIndex(activeIndex.value)
    else if (props.creatable && search.value.trim()) {
      const v = search.value.trim() as unknown as V
      emit('update:modelValue', v)
      emit('select', { value: v, label: search.value.trim() })
      open.value = false
      search.value = ''
    }
    e.preventDefault()
  } else if (e.key === 'Escape') {
    open.value = false
    e.preventDefault()
  }
}

function clear(): void {
  emit('update:modelValue', null)
  search.value = ''
}
</script>

<template>
  <div class="ui-combobox" :data-size="size" :data-error="!!error || undefined" @keydown="onKeydown">
    <div
      ref="floating.referenceRef"
      role="combobox"
      :aria-expanded="open"
      :aria-controls="listboxId"
      :aria-haspopup="'listbox'"
      :aria-invalid="!!error || undefined"
      :aria-label="ariaLabel"
      class="ui-combobox__field"
      tabindex="0"
      @click="open = !open"
    >
      <input
        :value="open ? search : selectedLabel"
        :placeholder="placeholder"
        :disabled="disabled"
        class="ui-combobox__input"
        :aria-activedescendant="activeIndex >= 0 ? `${localId}-opt-${activeIndex}` : undefined"
        @input="(e) => { search = (e.target as HTMLInputElement).value; open = true }"
        @focus="open = true"
      />
      <button
        v-if="clearable && modelValue != null"
        type="button"
        aria-label="Effacer"
        class="ui-combobox__clear"
        @click.stop="clear"
      >
        ×
      </button>
    </div>
    <div
      v-show="open"
      ref="floating.floatingRef"
      :id="listboxId"
      role="listbox"
      class="ui-combobox__list"
      :style="floating.floatingStyles.value"
      @scroll="onListScroll"
    >
      <div v-if="virtualize" :style="{ height: items.length * itemHeight + 'px', position: 'relative' }">
        <div
          v-for="vi in visibleItems"
          :key="String(vi.option.value)"
          :id="`${localId}-opt-${vi.index}`"
          role="option"
          :aria-selected="modelValue === vi.option.value"
          :data-active="activeIndex === vi.index || undefined"
          class="ui-combobox__option ui-combobox__option--virtual"
          :style="{ position: 'absolute', top: vi.index * itemHeight + 'px', height: itemHeight + 'px', left: 0, right: 0 }"
          @mousedown.prevent="selectOption(vi.option)"
        >
          <slot name="option" :option="vi.option" :selected="modelValue === vi.option.value">
            {{ vi.option.label }}
          </slot>
        </div>
      </div>
      <template v-else>
        <div
          v-for="vi in visibleItems"
          :key="String(vi.option.value)"
          :id="`${localId}-opt-${vi.index}`"
          role="option"
          :aria-selected="modelValue === vi.option.value"
          :data-active="activeIndex === vi.index || undefined"
          class="ui-combobox__option"
          @mousedown.prevent="selectOption(vi.option)"
        >
          <slot name="option" :option="vi.option" :selected="modelValue === vi.option.value">
            {{ vi.option.label }}
          </slot>
        </div>
      </template>
      <div v-if="items.length === 0 && !loading" class="ui-combobox__empty">
        <slot name="empty">{{ emptyText }}</slot>
      </div>
      <div v-if="loading" class="ui-combobox__loading">Chargement…</div>
    </div>
    <span v-if="helper && !error" class="ui-combobox__helper">{{ helper }}</span>
    <span v-if="error" class="ui-combobox__error" role="alert">{{ error }}</span>
  </div>
</template>

<style scoped>
.ui-combobox {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  position: relative;
}
.ui-combobox__field {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  background: var(--color-surface);
  min-height: 44px;
}
.ui-combobox[data-error] .ui-combobox__field {
  border-color: var(--color-danger-500);
}
.ui-combobox__field:focus-within {
  outline: 2px solid var(--color-focus-ring);
}
.ui-combobox__input {
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  font: inherit;
  font-family: var(--font-sans);
  color: var(--color-text);
}
.ui-combobox__clear {
  background: none;
  border: 0;
  cursor: pointer;
  font-size: var(--font-size-lg);
  color: var(--color-text-muted);
}
.ui-combobox__list {
  max-height: 16rem;
  overflow-y: auto;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  z-index: 20;
  min-width: 12rem;
}
.ui-combobox__option {
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  display: flex;
  align-items: center;
  min-height: 36px;
}
.ui-combobox__option[aria-selected='true'] {
  background: var(--color-brand-50);
}
.ui-combobox__option[data-active] {
  background: var(--color-neutral-100);
}
.ui-combobox__empty,
.ui-combobox__loading {
  padding: var(--space-3);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}
.ui-combobox__helper {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}
.ui-combobox__error {
  color: var(--color-danger-700);
  font-size: var(--font-size-xs);
}
</style>
