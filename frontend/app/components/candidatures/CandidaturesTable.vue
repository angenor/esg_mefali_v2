<script setup lang="ts">
// F51 T057 / T095 — Table candidatures avec filtre statut + tri updated_at desc.

import { computed, ref } from "vue"
import { useCandidaturesStore } from "~/stores/candidatures"
import type { CandidatureStatut } from "~/types/candidatures"

const store = useCandidaturesStore()

const statutFilter = ref<CandidatureStatut | "all">("all")
const search = ref("")

const filtered = computed(() => {
  const list = [...store.list]
  list.sort(
    (a, b) =>
      new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
  )
  return list.filter((c) => {
    if (statutFilter.value !== "all" && c.statut !== statutFilter.value)
      return false
    if (search.value.trim() !== "") {
      const q = search.value.trim().toLowerCase()
      if (!c.offre_nom?.toLowerCase().includes(q)) return false
    }
    return true
  })
})

const STATUT_LABEL: Record<CandidatureStatut, string> = {
  brouillon: "Brouillon",
  soumise: "Soumise",
  en_revue: "En revue",
  acceptee: "Acceptée",
  refusee: "Refusée",
}
const STATUT_COLOR: Record<CandidatureStatut, string> = {
  brouillon: "bg-gray-100 text-gray-800",
  soumise: "bg-blue-100 text-blue-800",
  en_revue: "bg-amber-100 text-amber-800",
  acceptee: "bg-green-100 text-green-800",
  refusee: "bg-red-100 text-red-800",
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center gap-3">
      <label class="text-sm font-medium">
        Statut
        <select
          v-model="statutFilter"
          class="ml-2 rounded border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="all">Tous</option>
          <option value="brouillon">Brouillons</option>
          <option value="soumise">Soumises</option>
          <option value="en_revue">En revue</option>
          <option value="acceptee">Acceptées</option>
          <option value="refusee">Refusées</option>
        </select>
      </label>
      <input
        v-model="search"
        type="search"
        placeholder="Rechercher par offre…"
        class="rounded border border-gray-300 px-3 py-1.5 text-sm"
      />
    </div>

    <div class="overflow-x-auto rounded-lg border border-gray-200">
      <table class="min-w-full divide-y divide-gray-200 text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-600">
          <tr>
            <th class="px-4 py-3">Offre</th>
            <th class="px-4 py-3">Statut</th>
            <th class="px-4 py-3">Progression</th>
            <th class="px-4 py-3">Mise à jour</th>
            <th class="px-4 py-3 text-right">Action</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-if="filtered.length === 0">
            <td colspan="5" class="px-4 py-8 text-center text-gray-500">
              Aucune candidature.
            </td>
          </tr>
          <tr v-for="c in filtered" :key="c.id" class="hover:bg-gray-50">
            <td class="px-4 py-3 font-medium">{{ c.offre_nom ?? "—" }}</td>
            <td class="px-4 py-3">
              <span
                class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
                :class="STATUT_COLOR[c.statut]"
              >
                {{ STATUT_LABEL[c.statut] }}
              </span>
            </td>
            <td class="px-4 py-3">
              <div class="flex items-center gap-2">
                <div class="h-2 w-24 rounded-full bg-gray-200">
                  <div
                    class="h-2 rounded-full bg-emerald-500"
                    :style="{ width: `${c.progression_pct}%` }"
                  />
                </div>
                <span class="text-xs text-gray-600">{{ c.progression_pct }}%</span>
              </div>
            </td>
            <td class="px-4 py-3 text-gray-600">
              {{ new Date(c.updated_at).toLocaleDateString("fr-FR") }}
            </td>
            <td class="px-4 py-3 text-right">
              <NuxtLink
                :to="`/candidatures/${c.id}`"
                class="text-emerald-700 hover:underline"
              >
                {{ c.statut === "brouillon" ? "Reprendre" : "Voir" }}
              </NuxtLink>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
