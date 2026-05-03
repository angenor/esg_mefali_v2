<script setup lang="ts">
// F44 T030 — Carte Rapports & attestations (cf. C-COMP-3 Rapports).
import { defineAsyncComponent } from "vue"
import UiCard from "~/components/ui/UiCard.vue"
import CardSkeleton from "./CardSkeleton.vue"
import CardErrorState from "./CardErrorState.vue"
import EmptyCardCTA from "./EmptyCardCTA.vue"
import { useT } from "~/composables/useT"
import type { CardKind, RapportsCardData } from "~/lib/mapSummaryToCardViewModels"

// Lazy : QR code chargé seulement client-side pour ne pas peser sur le SSR.
const QRCodeVue3 = defineAsyncComponent(() =>
  import("qrcode-vue3").then((m) => m.default),
)

interface Props {
  vm: CardKind<RapportsCardData>
}

const props = defineProps<Props>()
const { t } = useT()

function formatDate(d: Date): string {
  return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short", year: "numeric" }).format(d)
}
</script>

<template>
  <UiCard :aria-busy="props.vm.kind === 'loading' || undefined" data-testid="card-rapports">
    <template #header>
      <h2 class="card-title">{{ t("dashboard.cards.rapports.title") }}</h2>
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
    <div v-else class="card-rapports">
      <section v-if="props.vm.data.recentRapports.length > 0">
        <h3 class="card-rapports__sub">{{ t("dashboard.cards.rapports.recent_label") }}</h3>
        <ul class="card-rapports__list">
          <li v-for="r in props.vm.data.recentRapports" :key="r.id">
            <NuxtLink :to="r.downloadHref" data-testid="rapport-link">
              <strong>{{ r.title }}</strong>
              <span class="card-rapports__meta">
                {{ r.referentielsLabel }} · {{ formatDate(r.generatedAt) }}
              </span>
            </NuxtLink>
          </li>
        </ul>
      </section>
      <section v-if="props.vm.data.activeAttestations.length > 0">
        <h3 class="card-rapports__sub">{{ t("dashboard.cards.rapports.attestations_label") }}</h3>
        <ul class="card-rapports__qr-list">
          <li v-for="a in props.vm.data.activeAttestations" :key="a.id">
            <NuxtLink
              :to="a.verifyHref"
              :aria-label="t('dashboard.cards.rapports.verify_aria')"
              data-testid="attestation-qr"
              class="card-rapports__qr-link"
            >
              <ClientOnly>
                <QRCodeVue3 :value="a.verifyHref" :width="48" :height="48" />
              </ClientOnly>
              <span class="card-rapports__meta">{{ formatDate(a.validUntil) }}</span>
            </NuxtLink>
          </li>
        </ul>
      </section>
      <NuxtLink :to="props.vm.data.href" class="card-rapports__see-all">
        {{ t("dashboard.cards.intermediaires.see_all") }}
      </NuxtLink>
    </div>
  </UiCard>
</template>

<style scoped>
.card-title {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
}
.card-rapports {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.card-rapports__sub {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--color-text-muted, #666);
  margin: 0 0 0.25rem;
}
.card-rapports__list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  font-size: 0.875rem;
}
.card-rapports__list a {
  color: inherit;
  text-decoration: none;
  display: flex;
  flex-direction: column;
}
.card-rapports__meta {
  font-size: 0.75rem;
  color: var(--color-text-muted, #666);
}
.card-rapports__qr-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  gap: 0.75rem;
}
.card-rapports__qr-link {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  text-decoration: none;
  color: inherit;
}
.card-rapports__see-all {
  font-size: 0.8rem;
  color: var(--color-primary, #0a7d4d);
  text-decoration: none;
}
</style>
