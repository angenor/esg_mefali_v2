<script setup lang="ts">
// F49 T023 — ReportTable : table des rapports PME.
import { computed } from "vue"
import type { Rapport, RapportStatus } from "~/types/reports"
import { reportsApi } from "~/services/api/reports"

interface Props {
  reports: Rapport[]
  loading?: boolean
}
const props = withDefaults(defineProps<Props>(), { loading: false })
const emit = defineEmits<{
  (e: "select", rapportId: string): void
  (e: "regenerate", rapport: Rapport): void
}>()

const STATUS_LABELS: Record<RapportStatus, string> = {
  ready: "Prêt",
  generating: "En cours",
  failed: "Échec",
}

const STATUS_SEVERITY: Record<RapportStatus, "success" | "warning" | "error"> = {
  ready: "success",
  generating: "warning",
  failed: "error",
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date(iso))
  } catch {
    return ""
  }
}

function formatSize(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return "—"
  if (bytes < 1024) return `${bytes} o`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`
}

function formatPeriod(r: Rapport): string {
  if (!r.period_from || !r.period_to) return "—"
  return `${formatDate(r.period_from)} → ${formatDate(r.period_to)}`
}

function downloadUrl(id: string): string {
  return reportsApi.buildDownloadUrl(id)
}

const empty = computed(() => !props.loading && props.reports.length === 0)
</script>

<template>
  <div class="rounded-lg border border-gray-200 bg-white">
    <header class="flex items-center justify-between px-4 py-3 border-b border-gray-200">
      <h2 class="text-base font-semibold text-gray-900">Rapports PDF</h2>
    </header>
    <div v-if="loading" class="px-4 py-8 text-center text-sm text-gray-500">
      Chargement…
    </div>
    <div v-else-if="empty" class="px-4 py-8 text-center text-sm text-gray-500">
      <slot name="empty">Aucun rapport généré pour le moment.</slot>
    </div>
    <table v-else class="w-full text-sm" data-testid="report-table">
      <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
        <tr>
          <th scope="col" class="px-4 py-2 font-medium">Titre</th>
          <th scope="col" class="px-4 py-2 font-medium">Type</th>
          <th scope="col" class="px-4 py-2 font-medium">Période</th>
          <th scope="col" class="px-4 py-2 font-medium">Date</th>
          <th scope="col" class="px-4 py-2 font-medium">Taille</th>
          <th scope="col" class="px-4 py-2 font-medium">Statut</th>
          <th scope="col" class="px-4 py-2 font-medium text-right">Actions</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-gray-100">
        <tr
          v-for="r in props.reports"
          :key="r.id"
          class="hover:bg-gray-50 cursor-pointer focus-within:bg-gray-50"
          tabindex="0"
          :data-rapport-id="r.id"
          data-testid="report-row"
          @click="emit('select', r.id)"
          @keydown.enter.prevent="emit('select', r.id)"
        >
          <td class="px-4 py-3 font-medium text-gray-900">
            {{ r.download_filename }}
          </td>
          <td class="px-4 py-3 text-gray-700 capitalize">{{ r.type }}</td>
          <td class="px-4 py-3 text-gray-700">{{ formatPeriod(r) }}</td>
          <td class="px-4 py-3 text-gray-700">{{ formatDate(r.created_at) }}</td>
          <td class="px-4 py-3 text-gray-700">{{ formatSize(r.size_bytes) }}</td>
          <td class="px-4 py-3">
            <UiBadge :severity="STATUS_SEVERITY[r.status]" data-testid="status-chip">
              {{ STATUS_LABELS[r.status] }}
            </UiBadge>
          </td>
          <td class="px-4 py-3 text-right">
            <div class="flex justify-end gap-2" @click.stop>
              <a
                :href="downloadUrl(r.id)"
                class="rounded-md bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
                target="_blank"
                rel="noopener"
                data-testid="download-link"
              >
                Télécharger
              </a>
              <button
                type="button"
                class="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
                @click="emit('regenerate', r)"
                data-testid="regenerate-btn"
              >
                Régénérer
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
