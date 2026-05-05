<script setup lang="ts">
// F44 T029 — Carte Candidatures (cf. C-COMP-3 Candidatures).
import UiCard from "~/components/ui/UiCard.vue"
import UiBadge from "~/components/ui/UiBadge.vue"
import CardSkeleton from "./CardSkeleton.vue"
import CardErrorState from "./CardErrorState.vue"
import EmptyCardCTA from "./EmptyCardCTA.vue"
import { useT } from "~/composables/useT"
import type { CardKind, CandidaturesCardData } from "~/lib/mapSummaryToCardViewModels"

interface Props {
  vm: CardKind<CandidaturesCardData>
}

const props = defineProps<Props>()
const { t } = useT()

function formatDate(d: Date | null): string {
  if (!d) return t("dashboard.cards.candidatures.no_date")
  return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short", year: "numeric" }).format(d)
}
</script>

<template>
  <UiCard :aria-busy="props.vm.kind === 'loading' || undefined" data-testid="card-candidatures">
    <template #header>
      <h2 class="card-title">{{ t("dashboard.cards.candidatures.title") }}</h2>
    </template>

    <CardSkeleton v-if="props.vm.kind === 'loading'" :lines="4" />
    <EmptyCardCTA
      v-else-if="props.vm.kind === 'empty'"
      :cta="props.vm.cta"
      :message="props.vm.message"
    />
    <CardErrorState
      v-else-if="props.vm.kind === 'error'"
      :message="props.vm.message"
      @retry="props.vm.retry"
    />
    <NuxtLink v-else :to="props.vm.data.href" class="card-link">
      <div class="card-candidatures__pills">
        <UiBadge
          v-for="(count, statut) in props.vm.data.countersByStatut"
          :key="statut"
          severity="info"
          data-testid="counter-pill"
        >
          {{ t(`dashboard.statut.candidature.${statut}`) }}: {{ count }}
        </UiBadge>
      </div>
      <ul class="card-candidatures__list">
        <li v-for="c in props.vm.data.recent" :key="c.id" data-testid="candidature-recent">
          <span class="card-candidatures__label">{{ c.projetLabel }} · {{ c.offreLabel }}</span>
          <span class="card-candidatures__statut">{{ c.statutLabel }}</span>
          <span class="card-candidatures__date">{{ formatDate(c.soumissionAt) }}</span>
        </li>
      </ul>
    </NuxtLink>
  </UiCard>
</template>

<style scoped>
.card-title {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
}
.card-link {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  text-decoration: none;
  color: inherit;
}
.card-candidatures__pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.card-candidatures__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  font-size: 0.875rem;
}
.card-candidatures__list li {
  display: flex;
  flex-direction: column;
}
.card-candidatures__label {
  font-weight: 500;
}
.card-candidatures__statut,
.card-candidatures__date {
  font-size: 0.75rem;
  color: var(--color-text-muted, #666);
}
</style>
