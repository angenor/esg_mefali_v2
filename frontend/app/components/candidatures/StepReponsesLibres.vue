<script setup lang="ts">
// F51 T064 — Étape 4 : réponses libres (textarea simple par défaut + lien chat).
//
// Note : la version "complète" embarque ChatBottomSheet F41 ; ici, version
// dégradée fonctionnelle (textarea direct + bouton "Répondre via le chat").

import { computed, ref, watch } from "vue"
import { useCandidaturesStore } from "~/stores/candidatures"

const store = useCandidaturesStore()
const detail = computed(() => store.detail)

const reponses = ref<{ question: string; reponse: string }[]>([])

watch(
  detail,
  (d) => {
    const existing = d?.draft_snapshot_json?.step4?.reponses_libres ?? []
    if (existing.length === 0) {
      reponses.value = [
        {
          question: "Décrivez l'impact ESG attendu de ce projet.",
          reponse: "",
        },
        {
          question: "Comment ce projet s'inscrit-il dans votre stratégie de financement ?",
          reponse: "",
        },
      ]
    } else {
      reponses.value = existing.map((r) => ({
        question: r.question,
        reponse: r.reponse,
      }))
    }
  },
  { immediate: true },
)

const emit = defineEmits<{
  (e: "update", payload: { question: string; reponse: string; asked_at: string }[]): void
}>()

function emitAll(): void {
  const now = new Date().toISOString()
  emit(
    "update",
    reponses.value.map((r) => ({ ...r, asked_at: now })),
  )
}
</script>

<template>
  <section v-if="detail" class="space-y-6">
    <header>
      <h2 class="text-xl font-bold">Étape 4 — Réponses libres</h2>
      <p class="mt-1 text-sm text-gray-600">
        Quelques questions pour préciser votre dossier.
      </p>
    </header>

    <div
      v-for="(r, i) in reponses"
      :key="i"
      class="space-y-2 rounded-lg border border-gray-200 p-4"
    >
      <label :for="`q-${i}`" class="block font-medium">{{ r.question }}</label>
      <textarea
        :id="`q-${i}`"
        v-model="r.reponse"
        rows="4"
        class="w-full rounded border border-gray-300 px-3 py-2"
        @input="emitAll"
      />
    </div>
  </section>
</template>
