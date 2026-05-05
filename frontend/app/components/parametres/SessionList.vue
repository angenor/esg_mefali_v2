<script setup lang="ts">
// F52 US2 — Liste des sessions actives + bouton "Révoquer".
import { onMounted, ref } from 'vue'
import { useSessionsStore } from '~/stores/sessions'
import SessionRevokeBottomSheet from './SessionRevokeBottomSheet.vue'

const store = useSessionsStore()
const targetId = ref<string | null>(null)

onMounted(async () => {
  await store.load()
})

function openRevoke(id: string) {
  targetId.value = id
}
</script>

<template>
  <section class="rounded-lg border border-gray-200 bg-white p-4">
    <h2 class="text-lg font-semibold text-gray-900">Sessions actives</h2>
    <p v-if="store.loading" class="mt-2 text-xs text-gray-500">Chargement…</p>
    <ul v-else class="mt-3 divide-y divide-gray-100">
      <li
        v-for="s in store.items"
        :key="s.id"
        class="flex items-center justify-between py-3"
      >
        <div>
          <p class="text-sm font-medium text-gray-900">
            {{ s.device_label }}
            <span v-if="s.is_current" class="ml-2 rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-medium uppercase text-emerald-700">
              Courant
            </span>
          </p>
          <p class="text-xs text-gray-500">
            Dernière activité : {{ s.last_seen_at }}
            <span v-if="s.user_agent_summary"> · {{ s.user_agent_summary }}</span>
          </p>
        </div>
        <button
          v-if="!s.is_current"
          type="button"
          class="rounded border border-red-200 px-2 py-1 text-xs text-red-700 hover:bg-red-50"
          :data-testid="`session-revoke-${s.id}`"
          @click="openRevoke(s.id)"
        >
          Révoquer
        </button>
      </li>
    </ul>
    <SessionRevokeBottomSheet :session-id="targetId" @close="targetId = null" />
  </section>
</template>
