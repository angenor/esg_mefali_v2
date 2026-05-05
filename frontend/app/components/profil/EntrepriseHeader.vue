<script setup lang="ts">
// F43 T020 — En-tête profil entreprise : barre complétion + tooltip champs manquants + actions globales.
import { computed } from "vue"
import UiProgress from "~/components/ui/UiProgress.vue"
import { useT } from "~/composables/useT"
import type { MissingFeatureBlock } from "~/stores/entreprise"

interface Props {
  percentage: number
  missing?: MissingFeatureBlock[]
}

const props = withDefaults(defineProps<Props>(), { missing: () => [] })
const emit = defineEmits<{
  (e: "open-history"): void
}>()

const { t } = useT()

const completionLabel = computed(() =>
  t("profil.entreprise.completion.label", { pct: Math.round(props.percentage) }),
)

const tooltipFields = computed(() => {
  if (!props.missing?.length) return ""
  return props.missing
    .map((block) =>
      t("profil.entreprise.completion.missing_for_feature", {
        feature: block.feature_code,
        fields: block.missing_fields.join(", "),
      }),
    )
    .join("\n")
})
</script>

<template>
  <header class="entreprise-header">
    <div class="entreprise-header__title">
      <h1>{{ t("profil.entreprise.title") }}</h1>
      <p>{{ t("profil.entreprise.subtitle") }}</p>
    </div>
    <div class="entreprise-header__progress" :title="tooltipFields">
      <UiProgress :model-value="percentage" :aria-label="completionLabel" />
      <span class="entreprise-header__progress-label">{{ completionLabel }}</span>
      <button
        v-if="missing && missing.length > 0"
        type="button"
        class="entreprise-header__missing"
        :aria-describedby="undefined"
      >
        <abbr :title="tooltipFields">
          {{ t("profil.entreprise.completion.missing_label") }}
        </abbr>
      </button>
    </div>
    <div class="entreprise-header__actions">
      <button
        type="button"
        class="entreprise-header__btn"
        @click="emit('open-history')"
        data-testid="profil-history-btn"
      >
        {{ t("profil.entreprise.action.history") }}
      </button>
      <NuxtLink to="/chat" class="entreprise-header__btn entreprise-header__btn--ghost">
        {{ t("profil.entreprise.action.go_to_chat") }}
      </NuxtLink>
    </div>
  </header>
</template>

<style scoped>
.entreprise-header {
  display: grid;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 0.75rem;
}
.entreprise-header__title h1 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #0f172a;
}
.entreprise-header__title p {
  color: #475569;
  font-size: 0.875rem;
}
.entreprise-header__progress {
  display: grid;
  gap: 0.25rem;
}
.entreprise-header__progress-label {
  font-size: 0.875rem;
  color: #475569;
}
.entreprise-header__missing {
  align-self: start;
  background: transparent;
  border: 0;
  text-decoration: underline dotted;
  color: #b45309;
  cursor: help;
  font-size: 0.8125rem;
  padding: 0;
}
.entreprise-header__actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.entreprise-header__btn {
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  padding: 0.45rem 0.875rem;
  background: #fff;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  color: #0f172a;
}
.entreprise-header__btn--ghost {
  border-color: transparent;
  color: #15803d;
}
@media (min-width: 720px) {
  .entreprise-header {
    grid-template-columns: 2fr 1fr auto;
    align-items: center;
  }
}
</style>
