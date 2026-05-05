<script setup lang="ts">
// F49 T024 — AttestationTable : table des attestations PME.
import { computed } from "vue"
import type { Attestation, AttestationStatus } from "~/types/attestations"

interface Props {
  attestations: Attestation[]
  loading?: boolean
}
const props = withDefaults(defineProps<Props>(), { loading: false })
const emit = defineEmits<{
  (e: "share", attestation: Attestation): void
  (e: "revoke", attestation: Attestation): void
}>()

const STATUS_LABELS: Record<AttestationStatus, string> = {
  active: "Active",
  expired: "Expirée",
  revoked: "Révoquée",
}
const STATUS_SEVERITY: Record<AttestationStatus, "success" | "warning" | "error"> = {
  active: "success",
  expired: "warning",
  revoked: "error",
}
const TYPE_LABELS_FR: Record<string, string> = {
  conformite_esg: "Conformité ESG",
  bilan_carbone: "Bilan carbone",
  score_credit: "Score crédit",
  dossier_candidature: "Dossier candidature",
}

function formatDate(iso: string | null): string {
  if (!iso) return "—"
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

function canRevoke(a: Attestation): boolean {
  return a.status === "active"
}

const empty = computed(
  () => !props.loading && props.attestations.length === 0,
)
</script>

<template>
  <div class="rounded-lg border border-gray-200 bg-white">
    <header class="flex items-center justify-between px-4 py-3 border-b border-gray-200">
      <h2 class="text-base font-semibold text-gray-900">Attestations</h2>
    </header>
    <div v-if="loading" class="px-4 py-8 text-center text-sm text-gray-500">
      Chargement…
    </div>
    <div v-else-if="empty" class="px-4 py-8 text-center text-sm text-gray-500">
      <slot name="empty">Aucune attestation pour le moment.</slot>
    </div>
    <table v-else class="w-full text-sm" data-testid="attestation-table">
      <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
        <tr>
          <th scope="col" class="px-4 py-2 font-medium">Type</th>
          <th scope="col" class="px-4 py-2 font-medium">Statut</th>
          <th scope="col" class="px-4 py-2 font-medium">Émise</th>
          <th scope="col" class="px-4 py-2 font-medium">Expire</th>
          <th scope="col" class="px-4 py-2 font-medium">Identifiant public</th>
          <th scope="col" class="px-4 py-2 font-medium text-right">Actions</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-gray-100">
        <tr
          v-for="a in props.attestations"
          :key="a.id"
          data-testid="attestation-row"
        >
          <td class="px-4 py-3 font-medium text-gray-900">
            {{ TYPE_LABELS_FR[a.type] ?? a.type }}
          </td>
          <td class="px-4 py-3">
            <UiBadge :severity="STATUS_SEVERITY[a.status]">
              {{ STATUS_LABELS[a.status] }}
            </UiBadge>
          </td>
          <td class="px-4 py-3 text-gray-700">{{ formatDate(a.issued_at) }}</td>
          <td class="px-4 py-3 text-gray-700">{{ formatDate(a.expires_at) }}</td>
          <td class="px-4 py-3 font-mono text-xs text-gray-500">
            {{ a.public_id.slice(0, 12) }}…
          </td>
          <td class="px-4 py-3 text-right">
            <div class="flex justify-end gap-2">
              <button
                type="button"
                class="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
                @click="emit('share', a)"
                data-testid="share-btn"
              >
                Partager
              </button>
              <button
                type="button"
                class="rounded-md border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
                :disabled="!canRevoke(a)"
                @click="emit('revoke', a)"
                data-testid="revoke-btn"
              >
                Révoquer
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
