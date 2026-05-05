<script setup lang="ts">
// F52 US3 — Tableau historique des exports.
import type { ExportItem } from '~/stores/exports'

interface Props {
  items: ExportItem[]
  loading?: boolean
}
const props = defineProps<Props>()

function formatBytes(n: number | null): string {
  if (n === null || n === undefined) return '—'
  if (n < 1024) return `${n} o`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} ko`
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} Mo`
  return `${(n / 1024 / 1024 / 1024).toFixed(1)} Go`
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function statusLabel(s: ExportItem['status']): string {
  switch (s) {
    case 'pending':
      return 'En cours'
    case 'ready':
      return 'Prêt'
    case 'expired':
      return 'Expiré'
    case 'failed':
      return 'Échec'
  }
}

function typeLabel(t: ExportItem['type']): string {
  switch (t) {
    case 'rgpd_full':
      return 'Export RGPD complet'
    case 'report_pdf':
      return 'Rapport PDF'
    case 'attestation_pdf':
      return 'Attestation PDF'
    case 'dossier_pdf':
      return 'Dossier de candidature PDF'
  }
}
</script>

<template>
  <div data-testid="exports-table" class="overflow-x-auto">
    <table class="min-w-full text-left text-sm">
      <thead class="border-b border-gray-200 text-xs uppercase text-gray-500">
        <tr>
          <th class="px-3 py-2">Type</th>
          <th class="px-3 py-2">Format</th>
          <th class="px-3 py-2">Statut</th>
          <th class="px-3 py-2">Taille</th>
          <th class="px-3 py-2">Créé le</th>
          <th class="px-3 py-2">Action</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="props.loading" data-testid="exports-loading">
          <td colspan="6" class="px-3 py-6 text-center text-gray-400">
            Chargement…
          </td>
        </tr>
        <tr v-else-if="props.items.length === 0" data-testid="exports-empty">
          <td colspan="6" class="px-3 py-6 text-center text-gray-400">
            Aucun export pour le moment.
          </td>
        </tr>
        <tr
          v-for="item in props.items"
          :key="item.id"
          class="border-b border-gray-100 hover:bg-gray-50"
          :data-testid="`export-row-${item.id}`"
        >
          <td class="px-3 py-2 font-medium text-gray-900">
            {{ typeLabel(item.type) }}
          </td>
          <td class="px-3 py-2 uppercase text-gray-700">{{ item.format }}</td>
          <td class="px-3 py-2">
            <span
              class="inline-block rounded-full px-2 py-0.5 text-xs font-medium"
              :class="{
                'bg-yellow-100 text-yellow-800': item.status === 'pending',
                'bg-green-100 text-green-800': item.status === 'ready',
                'bg-gray-100 text-gray-700': item.status === 'expired',
                'bg-red-100 text-red-800': item.status === 'failed',
              }"
            >
              {{ statusLabel(item.status) }}
            </span>
          </td>
          <td class="px-3 py-2 text-gray-700">
            {{ formatBytes(item.size_bytes) }}
          </td>
          <td class="px-3 py-2 text-gray-700">
            {{ formatDate(item.created_at) }}
          </td>
          <td class="px-3 py-2">
            <a
              v-if="item.signed_url && item.status === 'ready'"
              :href="item.signed_url"
              class="text-brand-600 hover:underline"
              target="_blank"
              rel="noopener"
              :data-testid="`export-download-${item.id}`"
            >
              Télécharger
            </a>
            <span
              v-else-if="item.delivered_via === 'email'"
              class="text-xs text-gray-500"
            >
              Envoyé par e-mail
            </span>
            <span v-else class="text-xs text-gray-400">—</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
