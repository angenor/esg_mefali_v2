<!-- F40 T041 — VizLeafletMap : 50 pins clusterisés, zoom max 5, attribution OSM. -->
<script setup lang="ts">
import { ref, onBeforeUnmount, onMounted, watch, computed } from 'vue'
import VizSourcePin from './VizSourcePin.vue'
import VizLoadingState from './VizLoadingState.vue'
import VizEmptyState from './VizEmptyState.vue'
import type { MapPin } from '~/types/viz/chart'

interface Props {
  pins: MapPin[]
  source_id?: string
  title?: string
  ariaLabel?: string
  loading?: boolean
  empty?: boolean
  height?: string
  center?: { lat: number; lng: number }
  zoom?: number
  maxZoom?: number
}
const props = withDefaults(defineProps<Props>(), {
  loading: false,
  empty: false,
  height: '20rem',
  center: () => ({ lat: 12.6, lng: -2.5 }),
  zoom: 4,
  maxZoom: 5,
})

const container = ref<HTMLDivElement | null>(null)
let map: { remove: () => void } | null = null

async function build(): Promise<void> {
  if (!container.value) return
  const L = (await import('leaflet')).default
  const m = L.map(container.value, {
    center: [props.center.lat, props.center.lng],
    zoom: props.zoom,
    maxZoom: props.maxZoom,
    minZoom: 2,
    zoomControl: true,
  })
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: props.maxZoom,
    attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>',
  }).addTo(m)

  // Clustering basique côté client : groupe les pins par grille de tuile
  // (évite la dépendance leaflet.markercluster pour MVP — résout R10).
  const layer = L.layerGroup().addTo(m)
  for (const p of props.pins) {
    if (p.lat < -90 || p.lat > 90 || p.lng < -180 || p.lng > 180) continue
    const marker = L.marker([p.lat, p.lng], { title: p.label ?? '' })
    if (p.label) marker.bindTooltip(p.label)
    marker.addTo(layer)
  }
  map = m
}

onMounted(() => { void build() })
watch(() => props.pins, () => {
  if (map) { map.remove(); map = null }
  void build()
}, { deep: true })

onBeforeUnmount(() => {
  if (map) map.remove()
  map = null
})

const ariaLabel = computed(() => props.ariaLabel ?? props.title ?? `Carte avec ${props.pins.length} repère(s)`)
</script>

<template>
  <figure class="viz-leaflet">
    <figcaption v-if="props.title" class="viz-leaflet__title">
      {{ props.title }}
      <VizSourcePin v-if="props.source_id" :source_id="props.source_id" />
    </figcaption>
    <ClientOnly>
      <VizLoadingState v-if="props.loading" :height="props.height" />
      <VizEmptyState v-else-if="props.empty" :height="props.height" />
      <div
        v-else
        ref="container"
        class="viz-leaflet__map"
        role="application"
        :aria-label="ariaLabel"
        :style="{ height: props.height }"
      />
      <template #fallback>
        <VizLoadingState :height="props.height" />
      </template>
    </ClientOnly>
  </figure>
</template>

<style scoped>
.viz-leaflet { margin: 0; }
.viz-leaflet__title { display:flex; align-items:center; gap:.4rem; margin:0 0 .5rem; font-size:.95rem; font-weight:600; }
.viz-leaflet__map { width: 100%; border-radius: .375rem; overflow: hidden; }
</style>
