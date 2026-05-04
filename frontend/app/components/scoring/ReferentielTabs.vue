<script setup lang="ts">
// F46 T041 [US2] — Tabs référentiels (rôle tablist + nav clavier).
//
// Cf. specs/046-scoring-esg-ui/contracts/frontend-components.md §ReferentielTabs.
import { ref, nextTick } from "vue"
import { useT } from "~/composables/useT"

interface Props {
  availableCodes: string[]
  currentCode: string
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), { disabled: false })

const emit = defineEmits<{
  (e: "select", code: string): void
}>()

const { t } = useT()

const tabRefs = ref<HTMLButtonElement[]>([])

function setRef(el: Element | null, idx: number): void {
  if (el instanceof HTMLButtonElement) {
    tabRefs.value[idx] = el
  }
}

function onClick(code: string): void {
  if (props.disabled) return
  if (code === props.currentCode) return
  emit("select", code)
}

async function focusTab(idx: number): Promise<void> {
  await nextTick()
  const el = tabRefs.value[idx]
  if (el) el.focus()
}

function onKeydown(event: KeyboardEvent, idx: number): void {
  if (props.disabled) return
  const last = props.availableCodes.length - 1
  if (event.key === "ArrowRight") {
    event.preventDefault()
    const next = idx === last ? 0 : idx + 1
    void focusTab(next)
  } else if (event.key === "ArrowLeft") {
    event.preventDefault()
    const prev = idx === 0 ? last : idx - 1
    void focusTab(prev)
  } else if (event.key === "Home") {
    event.preventDefault()
    void focusTab(0)
  } else if (event.key === "End") {
    event.preventDefault()
    void focusTab(last)
  } else if (event.key === "Enter" || event.key === " ") {
    event.preventDefault()
    onClick(props.availableCodes[idx]!)
  }
}
</script>

<template>
  <div
    role="tablist"
    :aria-label="t('scoring.tabs.label')"
    class="ref-tabs"
    data-testid="referentiel-tabs"
  >
    <button
      v-for="(code, idx) in availableCodes"
      :key="code"
      :ref="(el) => setRef(el as Element | null, idx)"
      type="button"
      role="tab"
      :aria-selected="code === currentCode ? 'true' : 'false'"
      :tabindex="code === currentCode ? 0 : -1"
      :disabled="disabled"
      :data-code="code"
      class="ref-tabs__tab"
      :class="{ 'ref-tabs__tab--active': code === currentCode }"
      @click="onClick(code)"
      @keydown="onKeydown($event, idx)"
    >
      {{ code }}
    </button>
  </div>
</template>

<style scoped>
.ref-tabs {
  display: flex;
  gap: var(--space-2, 0.5rem);
  flex-wrap: wrap;
  padding: var(--space-1, 0.25rem) 0;
  border-bottom: 1px solid var(--color-neutral-200, #e5e5e5);
}
.ref-tabs__tab {
  font-family: inherit;
  font-size: var(--font-size-sm, 0.875rem);
  font-weight: 500;
  padding: var(--space-2, 0.5rem) var(--space-3, 0.75rem);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-md, 8px);
  color: var(--color-text-muted, #6b7280);
  cursor: pointer;
  transition: background 120ms, color 120ms;
}
.ref-tabs__tab:hover:not(:disabled) {
  background: var(--color-neutral-100, #f5f5f5);
  color: var(--color-text, #111827);
}
.ref-tabs__tab:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.ref-tabs__tab--active {
  background: var(--color-primary-50, #eff6ff);
  color: var(--color-primary-700, #1d4ed8);
  border-color: var(--color-primary-200, #bfdbfe);
}
.ref-tabs__tab:focus-visible {
  outline: 2px solid var(--color-primary-500, #3b82f6);
  outline-offset: 2px;
}
</style>
