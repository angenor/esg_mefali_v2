<script setup lang="ts">
// F51 T038 — Page /matching : liste cards + filtres + drawer + carte.

import { computed, onMounted, ref } from "vue"
import { useRoute } from "vue-router"
import { useMatchingStore } from "~/stores/matching"
import { useMatchingFilters } from "~/composables/useMatchingFilters"
import { useComparateur } from "~/composables/useComparateur"
import { useToast } from "~/composables/useToast"
import OffreCard from "~/components/matching/OffreCard.vue"
import FiltresPanel from "~/components/matching/FiltresPanel.vue"
import EmptyMatching from "~/components/matching/EmptyMatching.vue"
import OffreDrawer from "~/components/matching/OffreDrawer.vue"
import LeafletOffresMap from "~/components/matching/LeafletOffresMap.vue"
import type { MatchingFilters, OffreMatchItem } from "~/types/matching"

const route = useRoute()
const store = useMatchingStore()
const comparateur = useComparateur()
const toast = useToast()
const tab = ref<"liste" | "carte">("liste")

useMatchingFilters() // sync URL ↔ store

// Récupère le projet actif depuis la query (ou store user à brancher en US3 plus large)
const projetActifId = computed(() => {
  const fromQuery = String(route.query.projet ?? "").trim()
  return fromQuery || null
})

onMounted(async () => {
  store.setProjetActif(projetActifId.value)
  await store.fetchOffres()
})

const drawerOpen = computed(() => store.drawerOffreId !== null)

function onCardClick(offre: OffreMatchItem): void {
  void store.openDrawer(offre.offre_id)
}

function onAddToComparator(offre: OffreMatchItem): void {
  const ok = comparateur.add(offre, projetActifId.value)
  if (!ok) {
    toast.error("Maximum 3 offres comparables.")
  }
}

function onPinClick(offreId: string): void {
  void store.openDrawer(offreId)
}

function onFiltersUpdate(f: MatchingFilters): void {
  store.setFilters(f)
  void store.fetchOffres()
}

function gotoCompare(): void {
  navigateTo("/matching/compare")
}
</script>

<template>
  <main class="matching-page">
    <header class="matching-page__head">
      <h1>Trouvez votre financement vert</h1>
      <p>
        Explorez les offres compatibles avec votre projet ESG, comparez et
        préparez votre dossier en quelques clics.
      </p>
      <div class="matching-page__actions" role="tablist" aria-label="Affichage">
        <button
          role="tab"
          :aria-selected="tab === 'liste'"
          :class="{ 'is-active': tab === 'liste' }"
          @click="tab = 'liste'"
        >
          Liste
        </button>
        <button
          role="tab"
          :aria-selected="tab === 'carte'"
          :class="{ 'is-active': tab === 'carte' }"
          @click="tab = 'carte'"
        >
          Carte
        </button>
        <button
          v-if="comparateur.count.value > 0"
          class="matching-page__compare-btn"
          @click="gotoCompare"
        >
          Comparer ({{ comparateur.count.value }})
        </button>
      </div>
    </header>

    <FiltresPanel
      :model-value="store.filters"
      :loading="store.loading"
      @update:modelValue="onFiltersUpdate"
    />

    <p v-if="store.error" class="matching-page__error" role="alert">
      {{ store.error }}
    </p>

    <section v-if="tab === 'liste'" class="matching-page__list" aria-busy="store.loading">
      <EmptyMatching
        v-if="!store.loading && store.offres.length === 0"
        :has-projet="projetActifId !== null"
        :filtered="Object.keys(store.filters).length > 0"
        @create-projet="navigateTo('/profil/projets/nouveau')"
        @voir-toutes-offres="(store.setProjetActif(null), store.fetchOffres())"
        @reset="(store.setFilters({}), store.fetchOffres())"
      />
      <div v-else class="matching-page__cards">
        <OffreCard
          v-for="o in store.offres"
          :key="o.offre_id"
          :offre="o"
          :in-comparator="comparateur.has(o.offre_id)"
          :score-visible="store.isScoredMode"
          @click="onCardClick"
          @add-to-comparator="onAddToComparator"
          @remove-from-comparator="(o2) => comparateur.remove(o2.offre_id)"
        />
      </div>
    </section>

    <section v-else class="matching-page__map">
      <LeafletOffresMap :offres="store.offres" @pin-click="onPinClick" />
    </section>

    <OffreDrawer
      :open="drawerOpen"
      :projet-id="projetActifId"
      @close="store.closeDrawer()"
    />
  </main>
</template>

<style scoped>
.matching-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  max-width: 1180px;
  margin: 0 auto;
  padding: 1.5rem 1rem 4rem;
}
.matching-page__head h1 {
  margin: 0 0 0.25rem 0;
}
.matching-page__head p {
  color: var(--color-muted, #4b5563);
  margin: 0 0 1rem 0;
}
.matching-page__actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}
.matching-page__actions button {
  padding: 0.45rem 0.9rem;
  border: 1px solid var(--color-border, #d1d5db);
  background: white;
  border-radius: 0.4rem;
  cursor: pointer;
  font-size: 0.9rem;
}
.matching-page__actions button.is-active {
  background: var(--color-accent, #16a34a);
  color: white;
  border-color: var(--color-accent, #16a34a);
}
.matching-page__compare-btn {
  margin-left: auto;
}
.matching-page__error {
  color: #b91c1c;
  background: #fef2f2;
  padding: 0.6rem 0.9rem;
  border-radius: 0.5rem;
}
.matching-page__cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}
</style>
