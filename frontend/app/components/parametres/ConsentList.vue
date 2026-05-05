<script setup lang="ts">
// F52 US2 — Liste des consentements (lecture + retrait via bottom-sheet).
import { onMounted, ref } from 'vue'
import { useConsentsStore } from '~/stores/consents'
import ConsentWithdrawBottomSheet from './ConsentWithdrawBottomSheet.vue'

const store = useConsentsStore()
const targetId = ref<string | null>(null)

onMounted(async () => {
  await store.load()
})

function openWithdraw(id: string) {
  targetId.value = id
}
</script>

<template>
  <section class="rounded-lg border border-gray-200 bg-white p-4">
    <h2 class="text-lg font-semibold text-gray-900">Consentements</h2>
    <p v-if="store.loading" class="mt-2 text-xs text-gray-500">Chargement…</p>
    <p v-else-if="store.items.length === 0" class="mt-2 text-xs text-gray-500">
      Aucun consentement enregistré.
    </p>
    <ul v-else class="mt-3 divide-y divide-gray-100">
      <li v-for="c in store.items" :key="c.id" class="flex items-center justify-between py-3">
        <div>
          <p class="text-sm font-medium text-gray-900">{{ c.label }}</p>
          <p class="text-xs text-gray-500">
            {{ c.withdrawn_at ? `Retiré le ${c.withdrawn_at}` : (c.given_at ? `Accordé le ${c.given_at}` : 'En attente') }}
          </p>
        </div>
        <button
          v-if="!c.withdrawn_at && c.given_at"
          type="button"
          class="rounded border border-red-200 px-2 py-1 text-xs text-red-700 hover:bg-red-50"
          :data-testid="`consent-withdraw-${c.id}`"
          @click="openWithdraw(c.id)"
        >
          Retirer
        </button>
      </li>
    </ul>
    <ConsentWithdrawBottomSheet
      :consent-id="targetId"
      @close="targetId = null"
    />
  </section>
</template>
