<script setup lang="ts">
// F51 T065 — Étape 5 : récapitulatif lecture seule + checkbox + bouton Soumettre.
import { computed, ref } from "vue"
import { useCandidaturesStore } from "~/stores/candidatures"

const store = useCandidaturesStore()
const detail = computed(() => store.detail)
const acknowledged = ref(false)

const emit = defineEmits<{
  (e: "submit", acknowledged: boolean): void
  (e: "ack", value: boolean): void
}>()

function onAckChange(v: boolean): void {
  acknowledged.value = v
  emit("ack", v)
}
</script>

<template>
  <section v-if="detail" class="space-y-6">
    <header>
      <h2 class="text-xl font-bold">Étape 5 — Récapitulatif</h2>
      <p class="mt-1 text-sm text-gray-600">
        Vérifiez avant de soumettre. Une fois envoyée, votre candidature sera
        figée et non modifiable.
      </p>
    </header>

    <div class="space-y-4">
      <article class="rounded-lg border border-gray-200 p-4">
        <h3 class="font-semibold">Offre</h3>
        <p>{{ detail.offre.nom }}</p>
        <p class="text-sm text-gray-600">{{ detail.offre.intermediaire_nom }}</p>
      </article>
      <article class="rounded-lg border border-gray-200 p-4">
        <h3 class="font-semibold">Projet</h3>
        <p>{{ detail.projet.titre }}</p>
      </article>
      <article class="rounded-lg border border-gray-200 p-4">
        <h3 class="font-semibold">Documents joints</h3>
        <p class="text-sm text-gray-600">
          {{
            (detail.draft_snapshot_json.step3?.documents_links ?? []).length
          }}
          document(s) lié(s).
        </p>
      </article>
      <article class="rounded-lg border border-gray-200 p-4">
        <h3 class="font-semibold">Réponses</h3>
        <ul class="mt-2 space-y-2 text-sm">
          <li
            v-for="(r, i) in detail.draft_snapshot_json.step4?.reponses_libres ??
            []"
            :key="i"
          >
            <p class="font-medium">{{ r.question }}</p>
            <p class="text-gray-700">{{ r.reponse || "—" }}</p>
          </li>
        </ul>
      </article>
    </div>

    <label class="flex items-start gap-3 rounded-lg border border-amber-300 bg-amber-50 p-4">
      <input
        type="checkbox"
        :checked="acknowledged"
        class="mt-1"
        @change="onAckChange(($event.target as HTMLInputElement).checked)"
      />
      <span class="text-sm text-amber-900">
        J'ai compris que ma candidature, une fois soumise, sera
        <strong>figée et non modifiable</strong> (P4).
      </span>
    </label>

    <div class="flex justify-end">
      <button
        type="button"
        class="rounded-lg bg-emerald-600 px-6 py-3 font-semibold text-white shadow hover:bg-emerald-700 disabled:opacity-40"
        :disabled="!acknowledged || detail.progression_pct < 100"
        @click="emit('submit', acknowledged)"
      >
        Soumettre ma candidature
      </button>
    </div>
  </section>
</template>
