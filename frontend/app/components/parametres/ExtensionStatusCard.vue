<script setup lang="ts">
// F52 US5 — Carte d'état de l'extension navigateur (parametres/securite).
import { computed, onMounted } from 'vue'
import { useExtensionStatus } from '~/composables/useExtensionStatus'

const { state, refresh, forcePing } = useExtensionStatus()

const lastPingLabel = computed(() => {
  const iso = state.value.status.last_ping_at
  if (!iso) return 'Aucun ping reçu'
  const d = new Date(iso)
  return d.toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
})

onMounted(() => {
  void refresh()
})

async function handleSync() {
  await forcePing()
}
</script>

<template>
  <section
    class="rounded border border-gray-200 bg-white p-4 shadow-sm"
    data-testid="extension-status-card"
    aria-label="Extension navigateur"
  >
    <header class="mb-3 flex items-start justify-between gap-2">
      <div>
        <h3 class="text-sm font-semibold text-gray-900">Extension navigateur</h3>
        <p class="mt-1 text-xs text-gray-500">
          Détecte les pages BOAD/AFD et ouvre un panneau d'aide à la candidature.
        </p>
      </div>
      <span
        class="inline-block rounded-full px-2 py-0.5 text-xs font-medium"
        :class="
          state.status.detected
            ? 'bg-green-100 text-green-800'
            : 'bg-gray-100 text-gray-700'
        "
        data-testid="extension-detected-badge"
      >
        {{ state.status.detected ? 'Détectée' : 'Non détectée' }}
      </span>
    </header>

    <dl class="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
      <dt class="text-gray-500">Version</dt>
      <dd class="text-gray-900" data-testid="extension-version">
        {{ state.status.extension_version ?? '—' }}
      </dd>
      <dt class="text-gray-500">Dernier ping</dt>
      <dd class="text-gray-900" data-testid="extension-last-ping">
        {{ lastPingLabel }}
      </dd>
    </dl>

    <p
      v-if="state.error"
      class="mt-3 text-xs text-red-700"
      data-testid="extension-error"
    >
      Échec du chargement : {{ state.error }}
    </p>

    <div class="mt-3 flex justify-end gap-2">
      <button
        type="button"
        class="rounded border border-gray-200 bg-white px-3 py-1 text-xs"
        :disabled="state.loading"
        data-testid="extension-refresh-btn"
        @click="refresh"
      >
        Actualiser
      </button>
      <button
        type="button"
        class="rounded bg-brand-600 px-3 py-1 text-xs font-medium text-white disabled:opacity-50"
        :disabled="state.loading"
        data-testid="extension-sync-btn"
        @click="handleSync"
      >
        Synchroniser maintenant
      </button>
    </div>
  </section>
</template>
