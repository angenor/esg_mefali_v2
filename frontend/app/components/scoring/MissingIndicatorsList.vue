<script setup lang="ts">
// F46 T067 [US5] — Liste des indicateurs manquants + CTA Compléter (chat).
// Cf. specs/046-scoring-esg-ui/contracts/frontend-components.md §MissingIndicatorsList.
import { computed } from "vue"
import { useT } from "~/composables/useT"
import { useChatEventBus } from "~/composables/useChatEventBus"
import type { MissingIndicatorVM } from "~/types/scoring"

interface Props {
  missing: MissingIndicatorVM[]
  referentielCode: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: "complete", indicateurCode: string): void
}>()

const { t } = useT()
const bus = useChatEventBus()

const visible = computed<boolean>(() => props.missing.length > 0)

function onComplete(code: string, id: string): void {
  emit("complete", code)
  // Émission bus pour F41 (chat) + window event pour les écouteurs externes.
  bus.emit("entity_updated", {
    eventType: "entity_updated",
    entityType: "indicateur",
    entityId: id,
    fieldsUpdated: [code],
    source: "manual",
    ts: new Date().toISOString(),
  })
  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new CustomEvent("open_chat_for_indicateur", {
        detail: {
          indicateur_code: code,
          referentiel_code: props.referentielCode,
          source: "scoring_page",
        },
      }),
    )
  }
}
</script>

<template>
  <section
    v-if="visible"
    class="missing-indicators"
    data-testid="missing-indicators-list"
    :aria-label="t('scoring.missing.title')"
  >
    <header class="missing-indicators__header">
      <h2 class="missing-indicators__title">{{ t("scoring.missing.title") }}</h2>
      <p class="missing-indicators__description">
        {{ t("scoring.missing.description", { count: missing.length }) }}
      </p>
    </header>
    <ul class="missing-indicators__list">
      <li
        v-for="m in missing"
        :key="m.indicateurId"
        class="missing-indicators__item"
        :data-indicateur-code="m.indicateurCode"
      >
        <div class="missing-indicators__info">
          <span class="missing-indicators__code">{{ m.indicateurCode }}</span>
          <span class="missing-indicators__pillar">{{ m.pillar }}</span>
        </div>
        <button
          type="button"
          class="missing-indicators__cta"
          data-testid="missing-complete-cta"
          @click="onComplete(m.indicateurCode, m.indicateurId)"
        >
          {{ t("scoring.buttons.complete") }}
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.missing-indicators {
  background: var(--color-warning-50, #fffbeb);
  border: 1px solid var(--color-warning-200, #fde68a);
  border-radius: var(--radius-md, 8px);
  padding: var(--space-4, 1rem);
}
.missing-indicators__header {
  margin-bottom: var(--space-3, 0.75rem);
}
.missing-indicators__title {
  font-size: var(--font-size-lg, 1.125rem);
  font-weight: 600;
  margin: 0 0 var(--space-1, 0.25rem) 0;
}
.missing-indicators__description {
  font-size: var(--font-size-sm, 0.875rem);
  color: var(--color-text-muted, #6b7280);
  margin: 0;
}
.missing-indicators__list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 0.5rem);
}
.missing-indicators__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3, 0.75rem);
  padding: var(--space-2, 0.5rem) var(--space-3, 0.75rem);
  background: var(--color-surface, #fff);
  border-radius: var(--radius-sm, 4px);
}
.missing-indicators__info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.missing-indicators__code {
  font-family: var(--font-mono);
  font-size: var(--font-size-sm, 0.875rem);
  font-weight: 500;
}
.missing-indicators__pillar {
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-muted, #6b7280);
}
.missing-indicators__cta {
  background: var(--color-primary, #3b82f6);
  color: #fff;
  border: 0;
  border-radius: var(--radius-md, 8px);
  padding: var(--space-2, 0.5rem) var(--space-3, 0.75rem);
  cursor: pointer;
  font-size: var(--font-size-sm, 0.875rem);
  min-height: 36px;
}
.missing-indicators__cta:hover {
  background: var(--color-primary-600, #2563eb);
}
.missing-indicators__cta:focus-visible {
  outline: 2px solid var(--color-focus-ring, #3b82f6);
  outline-offset: 2px;
}
</style>
