<script setup lang="ts">
// F45 T023 — Timeline horizontale (verticale < 768 px) du plan d'action.
//
// Stagger gsap 80 ms désactivé si `reducedMotion`. Tooltip natif via `title`.
import { onMounted, ref } from "vue"
import type { TimelineBucketViewModel } from "~/types/actionPlan"

interface Props {
  buckets: TimelineBucketViewModel[]
  reducedMotion?: boolean
}

const props = withDefaults(defineProps<Props>(), { reducedMotion: false })
const emit = defineEmits<{
  (e: "select-step", stepId: string): void
}>()

const root = ref<HTMLElement | null>(null)

onMounted(async () => {
  if (props.reducedMotion || !root.value) return
  // Animation stagger gsap 80 ms — chargement dynamique pour ne pas l'embarquer
  // côté SSR si non utilisé.
  try {
    const mod = await import("gsap")
    const gsap = mod.gsap ?? mod.default ?? mod
    const items = root.value.querySelectorAll('[data-role="milestone"]')
    if (!items.length) return
    gsap.from(items, { opacity: 0, y: 8, duration: 0.32, stagger: 0.08, ease: "power2.out" })
  } catch {
    // gsap manquant → pas d'animation, l'UI reste fonctionnelle.
  }
})

function priorityColor(tone: "danger" | "warning" | "info"): string {
  return `pa-tone-${tone}`
}
</script>

<template>
  <section
    ref="root"
    class="pa-timeline"
    :class="{ 'pa-timeline--no-anim': reducedMotion }"
    data-testid="timeline"
    :data-orientation="'horizontal'"
    aria-label="Feuille de route du plan d'action"
  >
    <ol class="pa-timeline__buckets">
      <li
        v-for="bucket in buckets"
        :key="bucket.bucket"
        class="pa-timeline__bucket"
        :data-bucket="bucket.bucket"
      >
        <header class="pa-timeline__bucket-header">
          <span class="pa-timeline__bucket-label">{{ bucket.label }}</span>
          <span class="pa-timeline__bucket-count">{{ bucket.steps.length }}</span>
        </header>
        <ul class="pa-timeline__milestones">
          <li
            v-for="step in bucket.steps"
            :key="step.id"
            class="pa-timeline__milestone"
            data-role="milestone"
          >
            <button
              type="button"
              class="pa-timeline__dot"
              :class="priorityColor(step.priorityTone)"
              :title="step.title"
              :aria-label="step.title"
              @click="emit('select-step', step.id)"
            >
              <span class="visually-hidden">{{ step.title }}</span>
            </button>
          </li>
        </ul>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.pa-timeline {
  width: 100%;
  padding: var(--space-3) 0;
}
.pa-timeline__buckets {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space-3);
  list-style: none;
  margin: 0;
  padding: 0;
}
.pa-timeline__bucket {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-2);
  border-top: 2px solid var(--color-border-strong, #d1d5db);
  min-height: 96px;
}
.pa-timeline__bucket-header {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary, #4b5563);
}
.pa-timeline__milestones {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  list-style: none;
  margin: 0;
  padding: 0;
}
.pa-timeline__milestone { display: inline-flex; }
.pa-timeline__dot {
  width: 16px;
  height: 16px;
  border-radius: 999px;
  border: 0;
  cursor: pointer;
  background: var(--color-info-500, #3b82f6);
}
.pa-timeline__dot:focus-visible {
  outline: 2px solid var(--color-focus, #2563eb);
  outline-offset: 2px;
}
.pa-tone-danger { background: var(--color-danger-500, #ef4444); }
.pa-tone-warning { background: var(--color-warning-500, #f59e0b); }
.pa-tone-info { background: var(--color-info-500, #3b82f6); }
.visually-hidden {
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
@media (max-width: 767px) {
  .pa-timeline {
    --orientation: vertical;
  }
  .pa-timeline__buckets {
    grid-template-columns: 1fr;
  }
}
</style>
