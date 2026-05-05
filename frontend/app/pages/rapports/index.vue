<script setup lang="ts">
// F49 T022/T026/T027 — page Rapports & Attestations (PME).
import { onMounted, ref } from "vue"
import { useReportsStore } from "~/stores/reports"
import { useAttestationsStore } from "~/stores/attestations"
import ReportTable from "~/components/rapports/ReportTable.vue"
import AttestationTable from "~/components/rapports/AttestationTable.vue"
import ReportDrawer from "~/components/rapports/ReportDrawer.vue"
import GenerateReportModal from "~/components/rapports/GenerateReportModal.vue"
import ShareAttestationModal from "~/components/rapports/ShareAttestationModal.vue"
import RevokeAttestationModal from "~/components/rapports/RevokeAttestationModal.vue"
import type { Rapport } from "~/types/reports"
import type { Attestation } from "~/types/attestations"

definePageMeta({
  layout: "default",
  middleware: ["pme-only"],
  breadcrumb: [{ label: "Rapports & attestations" }],
  title: "Rapports & attestations",
})

const reports = useReportsStore()
const attestations = useAttestationsStore()

const selectedRapportId = ref<string | null>(null)
const drawerOpen = ref(false)
const generateOpen = ref(false)
const generatePrefill = ref<Partial<Rapport> | null>(null)
const shareTarget = ref<Attestation | null>(null)
const shareOpen = ref(false)
const revokeTarget = ref<Attestation | null>(null)
const revokeOpen = ref(false)

function openDrawer(id: string) {
  selectedRapportId.value = id
  drawerOpen.value = true
}
function closeDrawer() {
  drawerOpen.value = false
}
function openGenerate(prefill?: Rapport) {
  generatePrefill.value = prefill ? { ...prefill } : null
  generateOpen.value = true
}
function onGenerateClose() {
  generateOpen.value = false
  generatePrefill.value = null
}
function onShare(a: Attestation) {
  shareTarget.value = a
  shareOpen.value = true
}
function onShareClose() {
  shareOpen.value = false
  shareTarget.value = null
}
function onRevoke(a: Attestation) {
  revokeTarget.value = a
  revokeOpen.value = true
}
function onRevokeClose() {
  revokeOpen.value = false
  revokeTarget.value = null
}
async function onRevoked() {
  await attestations.fetchAll()
}

onMounted(async () => {
  // Chargement parallèle des deux ressources
  await Promise.all([reports.fetchAll(), attestations.fetchAll()])
  // Rattrapage FR-003a si des générations étaient en cours
  reports.rehydratePending()
})
</script>

<template>
  <div class="mx-auto max-w-6xl space-y-6 px-4 py-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Rapports &amp; attestations</h1>
        <p class="mt-1 text-sm text-gray-600">
          Téléchargez vos rapports PDF, partagez vos attestations vérifiables et
          gérez leur révocation.
        </p>
      </div>
      <button
        type="button"
        class="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
        @click="openGenerate()"
        data-testid="open-generate"
      >
        Nouveau rapport
      </button>
    </header>

    <ReportTable
      :reports="reports.reports"
      :loading="reports.loading"
      @select="openDrawer"
      @regenerate="(r) => openGenerate(r)"
    >
      <template #empty>
        <div class="space-y-2">
          <p>Vous n'avez encore généré aucun rapport.</p>
          <button
            type="button"
            class="rounded-md bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700"
            @click="openGenerate()"
            data-testid="empty-cta"
          >
            Générer mon premier rapport
          </button>
        </div>
      </template>
    </ReportTable>

    <AttestationTable
      :attestations="attestations.attestations"
      :loading="attestations.loading"
      @share="onShare"
      @revoke="onRevoke"
    >
      <template #empty>
        Vous n'avez encore aucune attestation. Générez-en une depuis votre
        tableau de bord pour pouvoir la partager.
      </template>
    </AttestationTable>

    <ReportDrawer
      :rapport-id="selectedRapportId"
      :open="drawerOpen"
      @close="closeDrawer"
    />

    <GenerateReportModal
      :open="generateOpen"
      :prefill="generatePrefill"
      @close="onGenerateClose"
    />

    <ShareAttestationModal
      :open="shareOpen"
      :attestation="shareTarget"
      @close="onShareClose"
    />

    <RevokeAttestationModal
      :open="revokeOpen"
      :attestation="revokeTarget"
      @close="onRevokeClose"
      @revoked="onRevoked"
    />
  </div>
</template>
