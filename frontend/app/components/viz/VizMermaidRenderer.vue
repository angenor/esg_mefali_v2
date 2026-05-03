<!-- F40 T033 — VizMermaidRenderer : rendu sanitisé + fallback texte. -->
<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { sanitizeMermaidSvg } from '~/utils/mermaidSanitize'
import VizSourcePin from './VizSourcePin.vue'
import VizLoadingState from './VizLoadingState.vue'
import type { MermaidPayload } from '~/types/viz/chart'

interface Props {
  payload: MermaidPayload
  source_id?: string
  title?: string
  ariaLabel?: string
  longDescription?: string
}
const props = defineProps<Props>()

const svg = ref<string>('')
const failed = ref(false)
const loading = ref(true)

let counter = 0

async function render(): Promise<void> {
  loading.value = true
  failed.value = false
  svg.value = ''
  if (typeof window === 'undefined') {
    loading.value = false
    return
  }
  try {
    const mermaid = (await import('mermaid')).default
    mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'default' })
    const id = props.payload.diagramId ?? `viz-mmd-${++counter}-${Date.now()}`
    const result = await mermaid.render(id, props.payload.script)
    let safe = sanitizeMermaidSvg(result.svg)
    if (props.ariaLabel && !safe.includes('<title>')) {
      safe = safe.replace(/<svg([^>]*)>/i, `<svg$1><title>${escapeXml(props.ariaLabel)}</title>`)
    }
    if (props.longDescription && !safe.includes('<desc>')) {
      safe = safe.replace(/<svg([^>]*)>/i, `<svg$1><desc>${escapeXml(props.longDescription)}</desc>`)
    }
    svg.value = safe
  }
  catch (e) {
    failed.value = true
    // eslint-disable-next-line no-console
    console.error('[VizMermaidRenderer] échec parsing, fallback texte.', e)
  }
  finally {
    loading.value = false
  }
}

function escapeXml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

onMounted(() => { void render() })
watch(() => props.payload.script, () => { void render() })
</script>

<template>
  <figure class="viz-mermaid">
    <figcaption v-if="props.title" class="viz-mermaid__title">
      {{ props.title }}
      <VizSourcePin v-if="props.source_id" :source_id="props.source_id" />
    </figcaption>
    <ClientOnly>
      <VizLoadingState v-if="loading" height="10rem" />
      <pre v-else-if="failed" class="viz-mermaid__fallback"><code class="language-mermaid">{{ props.payload.script }}</code></pre>
      <div
        v-else
        class="viz-mermaid__svg"
        role="img"
        :aria-label="props.ariaLabel ?? props.title ?? 'Diagramme Mermaid'"
        v-html="svg"
      />
      <template #fallback>
        <pre class="viz-mermaid__fallback"><code class="language-mermaid">{{ props.payload.script }}</code></pre>
      </template>
    </ClientOnly>
  </figure>
</template>

<style scoped>
.viz-mermaid { margin: 0; }
.viz-mermaid__title { display:flex; align-items:center; gap:.4rem; margin:0 0 .5rem; font-size:.95rem; font-weight:600; }
.viz-mermaid__svg :deep(svg) { max-width: 100%; height: auto; }
.viz-mermaid__fallback {
  padding: .75rem;
  background: var(--color-neutral-100, #f5f5f5);
  border: 1px dashed var(--color-neutral-300, #d4d4d4);
  border-radius: .5rem;
  font-family: var(--font-family-mono, "JetBrains Mono", monospace);
  font-size: .8rem;
  color: var(--color-neutral-700, #404040);
  overflow-x: auto;
  white-space: pre;
}
</style>
