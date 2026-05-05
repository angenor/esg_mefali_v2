<!--
  F40 — Wrapper interne canvas chart.js. Lazy-load chart.js + auto-import des
  contrôleurs nécessaires. SSR-safe : ne s'exécute que côté client (`<ClientOnly>`
  est apposé par les composants publics).
-->
<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, type PropType } from 'vue'
import { useChartTheme } from '~/composables/useChartTheme'

interface ChartConfigLike {
  type: string
  data: unknown
  options?: unknown
}

const props = defineProps({
  config: { type: Object as PropType<ChartConfigLike>, required: true },
  ariaLabel: { type: String, required: true },
  longDescription: { type: String, default: '' },
  height: { type: String, default: '16rem' },
})

const canvas = ref<HTMLCanvasElement | null>(null)
let chart: { update: () => void; destroy: () => void } | null = null
const theme = useChartTheme()

async function build(): Promise<void> {
  if (!canvas.value) return
  const mod = await import('chart.js/auto')
  const Chart = mod.default
  // theme integration via Chart.defaults
  Chart.defaults.font.family = theme.value.fonts.family
  Chart.defaults.font.size = theme.value.fonts.size
  Chart.defaults.color = theme.value.axis.color
  Chart.defaults.animation = theme.value.animations.reducedMotion
    ? false
    : { duration: theme.value.animations.duration }
  chart = new Chart(canvas.value, props.config as never) as never
}

onMounted(() => {
  void build()
})

watch(
  () => props.config,
  () => {
    if (chart) {
      chart.destroy()
      void build()
    }
  },
  { deep: true },
)

watch(theme, () => {
  if (chart) {
    chart.destroy()
    void build()
  }
})

onBeforeUnmount(() => {
  if (chart) chart.destroy()
  chart = null
})
</script>

<template>
  <div class="viz-canvas" :style="{ height }">
    <canvas
      ref="canvas"
      role="img"
      :aria-label="ariaLabel"
    />
    <span v-if="longDescription" class="sr-only">{{ longDescription }}</span>
  </div>
</template>

<style scoped>
.viz-canvas { position: relative; width: 100%; }
.viz-canvas canvas { width: 100% !important; height: 100% !important; }
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
