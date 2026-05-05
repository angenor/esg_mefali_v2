<script setup lang="ts">
// F51 T085 — 4 sliders + ARIA + formatMoney.
import { computed } from "vue"
import { useSimulateurStore } from "~/stores/simulateur"
import { formatMoney } from "~/utils/moneyFormat"
import type { TypeInvestissement } from "~/types/simulateur"

const store = useSimulateurStore()
const emit = defineEmits<{ (e: "change"): void }>()

const TYPES: { key: TypeInvestissement; label: string }[] = [
  { key: "renouvelable_solaire", label: "Solaire" },
  { key: "renouvelable_eolien", label: "Éolien" },
  { key: "efficacite_energetique", label: "Efficacité énergétique" },
  { key: "agriculture_durable", label: "Agriculture durable" },
  { key: "mobilite_electrique", label: "Mobilité électrique" },
  { key: "autre", label: "Autre" },
]

const montantNum = computed({
  get: () => Number(store.inputs.montant.amount),
  set: (v: number) => {
    store.setInput("montant", { ...store.inputs.montant, amount: String(v) })
    emit("change")
  },
})
const dureeNum = computed({
  get: () => store.inputs.duree_mois,
  set: (v: number) => {
    store.setInput("duree_mois", v)
    emit("change")
  },
})
const subvNum = computed({
  get: () => store.inputs.part_subvention_pct,
  set: (v: number) => {
    store.setInput("part_subvention_pct", v)
    emit("change")
  },
})
const typeInv = computed({
  get: () => store.inputs.type_investissement,
  set: (v: TypeInvestissement) => {
    store.setInput("type_investissement", v)
    emit("change")
  },
})
</script>

<template>
  <div class="space-y-6 rounded-lg border border-gray-200 bg-white p-5">
    <div>
      <label for="sl-montant" class="flex items-center justify-between font-medium">
        Montant à financer
        <span class="text-sm text-gray-600">{{ formatMoney(store.inputs.montant) }}</span>
      </label>
      <input
        id="sl-montant"
        v-model.number="montantNum"
        type="range"
        min="5000"
        max="2000000"
        step="5000"
        class="mt-2 w-full"
        :aria-valuetext="formatMoney(store.inputs.montant)"
      />
    </div>

    <div>
      <label for="sl-duree" class="flex items-center justify-between font-medium">
        Durée
        <span class="text-sm text-gray-600">{{ dureeNum }} mois</span>
      </label>
      <input
        id="sl-duree"
        v-model.number="dureeNum"
        type="range"
        min="6"
        max="240"
        step="6"
        class="mt-2 w-full"
      />
    </div>

    <div>
      <label for="sl-subv" class="flex items-center justify-between font-medium">
        Part subvention
        <span class="text-sm text-gray-600">{{ subvNum }} %</span>
      </label>
      <input
        id="sl-subv"
        v-model.number="subvNum"
        type="range"
        min="0"
        max="100"
        step="5"
        class="mt-2 w-full"
      />
    </div>

    <div>
      <label for="sl-type" class="block font-medium">Type d'investissement</label>
      <select
        id="sl-type"
        v-model="typeInv"
        class="mt-2 w-full rounded border border-gray-300 px-3 py-2"
      >
        <option v-for="t in TYPES" :key="t.key" :value="t.key">{{ t.label }}</option>
      </select>
    </div>
  </div>
</template>
