<script setup lang="ts">
// F51 T088 — Liste des simulations sauvegardées.
import { useSimulateurStore } from "~/stores/simulateur"
import { formatMoney } from "~/utils/money"

const store = useSimulateurStore()

async function onDelete(id: string): Promise<void> {
  if (typeof window !== "undefined" && !window.confirm("Supprimer cette simulation ?")) return
  await store.softDelete(id)
}
</script>

<template>
  <div class="overflow-x-auto rounded-lg border border-gray-200">
    <table class="min-w-full divide-y divide-gray-200 text-sm">
      <thead class="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-600">
        <tr>
          <th class="px-4 py-3">Nom</th>
          <th class="px-4 py-3">Coût total</th>
          <th class="px-4 py-3">CO₂ évité</th>
          <th class="px-4 py-3">Créée le</th>
          <th class="px-4 py-3 text-right">Action</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-gray-100">
        <tr v-if="store.history.length === 0">
          <td colspan="5" class="px-4 py-8 text-center text-gray-500">
            Aucune simulation sauvegardée.
          </td>
        </tr>
        <tr v-for="s in store.history" :key="s.id" class="hover:bg-gray-50">
          <td class="px-4 py-3 font-medium">{{ s.label }}</td>
          <td class="px-4 py-3">{{ formatMoney(s.results_summary.cout_total) }}</td>
          <td class="px-4 py-3">{{ s.results_summary.co2_evite_t }} t</td>
          <td class="px-4 py-3 text-gray-600">
            {{ new Date(s.created_at).toLocaleDateString("fr-FR") }}
          </td>
          <td class="px-4 py-3 text-right">
            <button
              type="button"
              class="text-sm text-red-600 hover:underline"
              @click="onDelete(s.id)"
            >
              Supprimer
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
