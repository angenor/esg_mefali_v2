<script setup lang="ts">
// F51 T059 — Étape 1 : récapitulatif offre + projet.
import { computed } from "vue"
import { useCandidaturesStore } from "~/stores/candidatures"
import { formatMoney } from "~/utils/money"

const store = useCandidaturesStore()
const detail = computed(() => store.detail)
</script>

<template>
  <section v-if="detail" class="space-y-6">
    <header>
      <h2 class="text-xl font-bold">Étape 1 — Offre & projet</h2>
      <p class="mt-1 text-sm text-gray-600">
        Vérifiez la cohérence entre votre projet et l'offre choisie. Vous
        pourrez modifier votre projet depuis la page « Mes projets ».
      </p>
    </header>

    <div class="grid gap-4 md:grid-cols-2">
      <article class="rounded-lg border border-gray-200 p-4">
        <h3 class="text-sm font-semibold uppercase tracking-wide text-gray-500">
          Offre sélectionnée
        </h3>
        <p class="mt-2 text-lg font-semibold">{{ detail.offre.nom }}</p>
        <p v-if="detail.offre.intermediaire_nom" class="text-sm text-gray-600">
          {{ detail.offre.intermediaire_nom }}
        </p>
        <p class="mt-2 text-sm">
          <span class="font-medium">Type :</span> {{ detail.offre.type }}
        </p>
        <p v-if="detail.offre.montant_min" class="text-sm text-gray-700">
          De {{ formatMoney(detail.offre.montant_min) }}
          <template v-if="detail.offre.montant_max">
            à {{ formatMoney(detail.offre.montant_max) }}
          </template>
        </p>
      </article>

      <article class="rounded-lg border border-gray-200 p-4">
        <h3 class="text-sm font-semibold uppercase tracking-wide text-gray-500">
          Projet
        </h3>
        <p class="mt-2 text-lg font-semibold">{{ detail.projet.titre }}</p>
        <p v-if="detail.projet.description" class="mt-2 text-sm text-gray-700">
          {{ detail.projet.description }}
        </p>
      </article>
    </div>
  </section>
</template>
