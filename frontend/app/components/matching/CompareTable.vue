<script setup lang="ts">
// F51 T036 — Table comparateur side-by-side (max 3 offres).

import { computed, onMounted, ref } from "vue"
import { offresApi } from "~/services/api/offres"
import { useComparateur } from "~/composables/useComparateur"
import { formatMoney } from "~/utils/moneyFormat"
import type { OffreDetail } from "~/types/matching"

const comparateur = useComparateur()
const details = ref<OffreDetail[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const ids = comparateur.entries.value.map((e) => e.offre_id)
    const all = await Promise.all(ids.map((id) => offresApi.getDetail(id)))
    details.value = all
  } catch (e) {
    error.value = (e as Error).message ?? "load_failed"
  } finally {
    loading.value = false
  }
}

onMounted(load)

const headers = computed(() => details.value.map((d) => d.nom))

function montant(d: OffreDetail): string {
  if (d.montant_min && d.montant_max) {
    return `${formatMoney(d.montant_min)} – ${formatMoney(d.montant_max)}`
  }
  if (d.montant_max) return `Jusqu'à ${formatMoney(d.montant_max)}`
  if (d.montant_min) return `À partir de ${formatMoney(d.montant_min)}`
  return "—"
}

function duree(d: OffreDetail): string {
  if (d.duree_min_mois && d.duree_max_mois) return `${d.duree_min_mois} – ${d.duree_max_mois} mois`
  if (d.duree_max_mois) return `Jusqu'à ${d.duree_max_mois} mois`
  if (d.duree_min_mois) return `À partir de ${d.duree_min_mois} mois`
  return "—"
}

function remove(id: string): void {
  comparateur.remove(id)
  details.value = details.value.filter((d) => d.offre_id !== id)
}
</script>

<template>
  <section class="compare-table" aria-label="Comparateur d'offres">
    <h2>Comparateur d'offres ({{ details.length }} / 3)</h2>
    <p v-if="error" class="compare-table__error">{{ error }}</p>
    <p v-else-if="loading">Chargement…</p>
    <p v-else-if="!details.length">Aucune offre dans le comparateur.</p>

    <table v-else class="compare-table__grid">
      <caption class="sr-only">Comparaison côte à côte des offres sélectionnées</caption>
      <thead>
        <tr>
          <th scope="col" />
          <th v-for="d in details" :key="d.offre_id" scope="col">
            <div class="compare-table__col-head">
              <span>{{ d.nom }}</span>
              <button type="button" :aria-label="`Retirer ${d.nom}`" @click="remove(d.offre_id)">×</button>
            </div>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th scope="row">Intermédiaire</th>
          <td v-for="d in details" :key="d.offre_id">{{ d.intermediaire.nom }}</td>
        </tr>
        <tr>
          <th scope="row">Type</th>
          <td v-for="d in details" :key="d.offre_id">{{ d.type }}</td>
        </tr>
        <tr>
          <th scope="row">Montant</th>
          <td v-for="d in details" :key="d.offre_id">{{ montant(d) }}</td>
        </tr>
        <tr>
          <th scope="row">Durée</th>
          <td v-for="d in details" :key="d.offre_id">{{ duree(d) }}</td>
        </tr>
        <tr>
          <th scope="row">Secteurs</th>
          <td v-for="d in details" :key="d.offre_id">
            {{ d.secteurs.join(", ") || "—" }}
          </td>
        </tr>
        <tr>
          <th scope="row">Documents requis</th>
          <td v-for="d in details" :key="d.offre_id">
            <ul v-if="d.documents_requis.length">
              <li v-for="doc in d.documents_requis" :key="doc.key">{{ doc.label }}</li>
            </ul>
            <span v-else>—</span>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.compare-table {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.compare-table h2 {
  margin: 0;
}
.compare-table__error {
  color: #b91c1c;
}
.compare-table__grid {
  width: 100%;
  border-collapse: collapse;
  border: 1px solid var(--color-border, #e5e7eb);
}
.compare-table__grid th,
.compare-table__grid td {
  padding: 0.6rem 0.8rem;
  border: 1px solid var(--color-border, #e5e7eb);
  text-align: left;
  font-size: 0.9rem;
  vertical-align: top;
}
.compare-table__grid thead th {
  background: var(--color-surface-alt, #f9fafb);
  position: sticky;
  top: 0;
}
.compare-table__grid tbody th[scope="row"] {
  background: var(--color-surface-alt, #f9fafb);
  position: sticky;
  left: 0;
  font-weight: 500;
  width: 12rem;
}
.compare-table__col-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}
.compare-table__col-head button {
  background: transparent;
  border: 0;
  font-size: 1.1rem;
  cursor: pointer;
  color: var(--color-muted, #6b7280);
}
.compare-table__grid ul {
  margin: 0;
  padding-left: 1.1rem;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}
</style>
