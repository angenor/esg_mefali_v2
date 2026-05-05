<script setup lang="ts">
// F51 T035 — Carte Leaflet des intermédiaires (chunk async).
//
// Cf. research.md §5. Pas de @vue-leaflet/vue-leaflet : on consomme l'API
// Leaflet directement via composable maison.

import { onMounted, onBeforeUnmount, ref, watch } from "vue"
import type { OffreMatchItem } from "~/types/matching"

const props = defineProps<{
  offres: OffreMatchItem[]
}>()

const emit = defineEmits<{
  "pin-click": [offreId: string]
}>()

const mapEl = ref<HTMLDivElement | null>(null)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let map: any = null
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let markers: any[] = []

async function initMap(): Promise<void> {
  if (!mapEl.value) return
  if (typeof window === "undefined") return
  // Import dynamique : ne tirer Leaflet (~150 ko) que si la carte est rendue.
  const L = (await import("leaflet")).default
  await import("leaflet/dist/leaflet.css")
  if (!mapEl.value) return
  // Centre par défaut : Côte d'Ivoire (Abidjan).
  map = L.map(mapEl.value, { zoomControl: true }).setView([5.31, -4.04], 5)
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors",
    maxZoom: 18,
  }).addTo(map)
  renderMarkers(L)
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function renderMarkers(L: any): void {
  if (!map) return
  // Clear existing markers.
  for (const m of markers) map.removeLayer(m)
  markers = []
  for (const o of props.offres) {
    const g = o.intermediaire.geolocation
    if (!g) continue
    const marker = L.marker([g.lat, g.lng]).addTo(map)
    marker.bindPopup(`<strong>${escape(o.intermediaire.nom)}</strong><br>${escape(o.nom)}`)
    marker.on("click", () => emit("pin-click", o.offre_id))
    markers.push(marker)
  }
}

function escape(s: string): string {
  return s.replace(/[&<>"']/g, (c) => {
    const map: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#x27;",
    }
    return map[c] ?? c
  })
}

const hasGeolocated = () =>
  props.offres.some((o) => o.intermediaire.geolocation !== null)

onMounted(() => {
  if (hasGeolocated()) {
    void initMap()
  }
})

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
    markers = []
  }
})

watch(
  () => props.offres,
  async () => {
    if (!map && hasGeolocated()) {
      await initMap()
      return
    }
    if (map) {
      const L = (await import("leaflet")).default
      renderMarkers(L)
    }
  },
  { deep: true },
)
</script>

<template>
  <div class="leaflet-offres-map">
    <div
      v-if="!offres.some((o) => o.intermediaire.geolocation)"
      class="leaflet-offres-map__empty"
      role="status"
    >
      Aucun intermédiaire géolocalisé pour l'instant — la carte est vide.
    </div>
    <div ref="mapEl" class="leaflet-offres-map__canvas" />
  </div>
</template>

<style scoped>
.leaflet-offres-map {
  position: relative;
  height: 480px;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 0.75rem;
  overflow: hidden;
}
.leaflet-offres-map__canvas {
  width: 100%;
  height: 100%;
}
.leaflet-offres-map__empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 1rem;
  color: var(--color-muted, #6b7280);
  background: var(--color-surface-alt, #f9fafb);
  z-index: 1;
}
</style>
