<script setup lang="ts">
// F43 T063 — HistoryDrawer : drawer latéral listant l'audit log paginé d'une entité.
//
// Consomme `GET /me/audit-log?entity=...&entity_id=...&cursor=...`.
// Slide-in 200 ms via gsap (respecte prefers-reduced-motion).
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue"
import { gsap } from "gsap"
import { useT, type LocaleKey } from "~/composables/useT"
import { useFocusTrap } from "~/composables/useFocusTrap"
import { useReducedMotion } from "~/composables/useReducedMotion"

interface AuditEntry {
  id: string
  entity: string
  entity_id: string
  field: string
  old: unknown
  new: unknown
  source_of_change: "manual" | "llm" | "import" | "admin"
  user_id?: string | null
  ts: string
}

interface AuditLogPage {
  items: AuditEntry[]
  next_cursor?: string | null
}

interface Props {
  open: boolean
  entity: "entreprise" | "projet"
  entityId?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{ (e: "close"): void }>()

const { t } = useT()
const reduced = useReducedMotion()
const drawerRef = ref<HTMLElement | null>(null)
const trap = useFocusTrap(drawerRef, { returnFocus: true })

const items = ref<AuditEntry[]>([])
const cursor = ref<string | null>(null)
const loading = ref(false)
const initialized = ref(false)

async function fetchPage(): Promise<void> {
  if (loading.value) return
  loading.value = true
  try {
    const config = useRuntimeConfig()
    const apiBase = config.public.apiBase as string
    const params = new URLSearchParams({ entity: props.entity })
    if (props.entityId) params.set("entity_id", props.entityId)
    if (cursor.value) params.set("cursor", cursor.value)
    const page = await $fetch<AuditLogPage>(
      `${apiBase}/me/audit-log?${params.toString()}`,
      { credentials: "include" },
    )
    items.value = [...items.value, ...page.items]
    cursor.value = page.next_cursor ?? null
    initialized.value = true
  } catch {
    initialized.value = true
  } finally {
    loading.value = false
  }
}

function reset(): void {
  items.value = []
  cursor.value = null
  initialized.value = false
}

function onKeydown(e: KeyboardEvent): void {
  if (props.open && e.key === "Escape") {
    e.preventDefault()
    emit("close")
  }
}

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      reset()
      await nextTick()
      trap.activate()
      document.addEventListener("keydown", onKeydown, true)
      void fetchPage()
      if (!reduced.value && drawerRef.value) {
        gsap.fromTo(
          drawerRef.value,
          { x: 360, opacity: 0 },
          { x: 0, opacity: 1, duration: 0.2, ease: "power1.out" },
        )
      }
    } else {
      trap.deactivate()
      document.removeEventListener("keydown", onKeydown, true)
    }
  },
)

onBeforeUnmount(() => {
  trap.deactivate()
  document.removeEventListener("keydown", onKeydown, true)
})

function formatValue(v: unknown): string {
  if (v == null) return "—"
  if (typeof v === "object") {
    try {
      return JSON.stringify(v)
    } catch {
      return String(v)
    }
  }
  return String(v)
}

function sourceLabel(s: AuditEntry["source_of_change"]): string {
  const k = `profil.projets.history.source.${s}` as LocaleKey
  return t(k)
}

const hasMore = computed(() => cursor.value != null)
</script>

<template>
  <Teleport v-if="open" to="body">
    <div class="history-drawer">
      <div class="history-drawer__overlay" @click="emit('close')" />
      <aside
        ref="drawerRef"
        role="dialog"
        aria-modal="true"
        aria-labelledby="history-drawer-title"
        tabindex="-1"
        class="history-drawer__panel"
      >
        <header class="history-drawer__header">
          <h2 id="history-drawer-title">{{ t("profil.projets.history.title") }}</h2>
          <button
            type="button"
            class="history-drawer__close"
            :aria-label="'Fermer'"
            @click="emit('close')"
          >
            ×
          </button>
        </header>
        <div class="history-drawer__body">
          <p v-if="!initialized" aria-live="polite">Chargement…</p>
          <p v-else-if="items.length === 0">{{ t("profil.projets.history.empty") }}</p>
          <ul v-else class="history-drawer__list">
            <li v-for="entry in items" :key="entry.id" class="history-drawer__item">
              <div class="history-drawer__row">
                <strong>{{ entry.field }}</strong>
                <span class="history-drawer__badge" :data-source="entry.source_of_change">
                  {{ sourceLabel(entry.source_of_change) }}
                </span>
              </div>
              <div class="history-drawer__values">
                <span class="history-drawer__old">{{ formatValue(entry.old) }}</span>
                <span aria-hidden="true">→</span>
                <span class="history-drawer__new">{{ formatValue(entry.new) }}</span>
              </div>
              <p class="history-drawer__meta">
                {{ new Date(entry.ts).toLocaleString("fr-FR") }}
              </p>
            </li>
          </ul>
          <button
            v-if="hasMore"
            type="button"
            class="history-drawer__more"
            :disabled="loading"
            @click="fetchPage"
          >
            {{ t("profil.projets.history.load_more") }}
          </button>
        </div>
      </aside>
    </div>
  </Teleport>
</template>

<style scoped>
.history-drawer {
  position: fixed;
  inset: 0;
  z-index: 1100;
}
.history-drawer__overlay {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
}
.history-drawer__panel {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: min(360px, 100%);
  background: #fff;
  box-shadow: -10px 0 25px -5px rgba(15, 23, 42, 0.15);
  display: grid;
  grid-template-rows: auto 1fr;
}
.history-drawer__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #e2e8f0;
}
.history-drawer__header h2 {
  font-size: 1rem;
  font-weight: 600;
}
.history-drawer__close {
  background: none;
  border: 0;
  font-size: 1.5rem;
  cursor: pointer;
  line-height: 1;
}
.history-drawer__body {
  padding: 1rem 1.25rem;
  overflow-y: auto;
}
.history-drawer__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.75rem;
}
.history-drawer__item {
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 0.625rem;
}
.history-drawer__row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}
.history-drawer__row strong {
  font-size: 0.875rem;
  color: #0f172a;
}
.history-drawer__badge {
  font-size: 0.6875rem;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-weight: 600;
  background: #f1f5f9;
  color: #475569;
}
.history-drawer__badge[data-source="llm"] {
  background: #ede9fe;
  color: #5b21b6;
}
.history-drawer__badge[data-source="manual"] {
  background: #dcfce7;
  color: #166534;
}
.history-drawer__values {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.8125rem;
  margin-top: 0.25rem;
  flex-wrap: wrap;
}
.history-drawer__old {
  color: #94a3b8;
  text-decoration: line-through;
}
.history-drawer__new {
  color: #0f172a;
  font-weight: 500;
}
.history-drawer__meta {
  color: #64748b;
  font-size: 0.75rem;
  margin-top: 0.25rem;
}
.history-drawer__more {
  width: 100%;
  margin-top: 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  padding: 0.5rem;
  background: #fff;
  cursor: pointer;
  font-weight: 500;
}
</style>
