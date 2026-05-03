<script setup lang="ts">
// F44 T054 [US6] — Wrapper léger pour matérialiser le sourçage P1 sur les cartes ESG.
//
// Note dégradation : F32 (summary endpoint) n'expose pas (encore) les `source_ids`
// par indicateur dans `summary.scores[*]` / `summary.carbon[*]`. En attendant,
// nous affichons un badge avec le `count` cliquable. Le clic ouvre un popover
// qui annonce que la liste détaillée est disponible sur la page détail.
// TODO post-MVP : brancher `source_ids` quand F32 les expose, alors le popover
// affichera la liste des sources (titre + date) directement.
import { ref } from "vue"
import { useT } from "~/composables/useT"

interface Props {
  count: number
  detailHref: string
}

const props = defineProps<Props>()
const { t } = useT()
const open = ref(false)

function toggle(): void {
  if (props.count <= 0) return
  open.value = !open.value
}
</script>

<template>
  <div class="source-list" data-testid="dashboard-source-list">
    <button
      type="button"
      class="source-list__pin"
      :disabled="props.count <= 0"
      :aria-expanded="open"
      :aria-label="t('dashboard.cards.scoring.sources', { count: props.count })"
      data-testid="source-pin"
      @click.stop.prevent="toggle"
    >
      {{ t("dashboard.cards.scoring.sources", { count: props.count }) }}
    </button>
    <div
      v-if="open"
      class="source-list__pop"
      role="dialog"
      data-testid="source-list-pop"
    >
      <p>{{ t("dashboard.cards.scoring.source_pop_message") }}</p>
      <NuxtLink :to="props.detailHref" class="source-list__link">
        {{ t("dashboard.cards.scoring.source_pop_link") }}
      </NuxtLink>
    </div>
  </div>
</template>

<style scoped>
.source-list {
  position: relative;
  display: inline-block;
}
.source-list__pin {
  background: none;
  border: 1px dashed var(--color-border, #ccc);
  border-radius: 999px;
  padding: 0.125rem 0.5rem;
  font-size: 0.7rem;
  color: var(--color-text-muted, #555);
  cursor: pointer;
}
.source-list__pin:disabled {
  cursor: default;
  opacity: 0.6;
}
.source-list__pin:hover:not(:disabled),
.source-list__pin:focus-visible:not(:disabled) {
  border-color: var(--color-primary, #0a7d4d);
  color: var(--color-primary, #0a7d4d);
  outline: 2px solid var(--color-focus, #0a7d4d);
  outline-offset: 2px;
}
.source-list__pop {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 0.25rem;
  padding: 0.5rem;
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border, #ddd);
  border-radius: 0.375rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  font-size: 0.75rem;
  z-index: 5;
  min-width: 180px;
}
.source-list__link {
  color: var(--color-primary, #0a7d4d);
  text-decoration: underline;
}
</style>
