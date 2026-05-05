<script setup lang="ts">
/**
 * MessageBubbleAssistant — bulle assistant (gauche).
 *
 * F41 / US1 (T015) + US5 (T039) + US7 (T048) + US3 (T033).
 * Slot dynamique selon `payload.kind` :
 *   - null → MessageMarkdown (text)
 *   - 'viz' → composant F40 approprié selon `payload.tool`
 *   - 'error' → MessageError
 *   - 'sheet_result' → MessageMarkdown (résumé textuel)
 *
 * P10 strict : aucune primitive interactive ici. Émet `cite-click` et `retry`.
 */
import { computed } from 'vue'
import type { MessagePayload, VizTool, ChatErrorCode } from '~/types/chat'
import MessageMarkdown from './MessageMarkdown.vue'
import MessageError from './MessageError.vue'
import {
  VizKPICard,
  VizLineChart,
  VizAreaChart,
  VizBarChart,
  VizStackedBarChart,
  VizRadarChart,
  VizGaugeChart,
  VizPieChart,
  VizDonutChart,
  VizMermaidRenderer,
  VizDataTable,
  VizLeafletMap,
} from '~/components/viz'

interface Props {
  messageId: string
  content: string
  payload: MessagePayload | null
  streaming?: boolean
  hasMutation?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  streaming: false,
  hasMutation: false,
})

const emit = defineEmits<{
  (e: 'retry', messageId: string): void
  (e: 'cite-click', sourceId: string): void
}>()

const VIZ_MAP: Record<VizTool, unknown> = {
  kpi: VizKPICard,
  line: VizLineChart,
  area: VizAreaChart,
  bar: VizBarChart,
  stacked_bar: VizStackedBarChart,
  radar: VizRadarChart,
  gauge: VizGaugeChart,
  pie: VizPieChart,
  donut: VizDonutChart,
  mermaid: VizMermaidRenderer,
  table: VizDataTable,
  map: VizLeafletMap,
}

const isViz = computed(() => props.payload?.kind === 'viz')
const isError = computed(() => props.payload?.kind === 'error')
const vizComponent = computed(() => {
  if (props.payload?.kind !== 'viz') return null
  return VIZ_MAP[props.payload.tool] ?? null
})
const vizData = computed(() => {
  if (props.payload?.kind !== 'viz') return null
  return props.payload.data
})
const isClientOnlyViz = computed(() => {
  if (props.payload?.kind !== 'viz') return false
  return props.payload.tool === 'mermaid' || props.payload.tool === 'map'
})

const errorCode = computed<ChatErrorCode>(() => {
  if (props.payload?.kind === 'error') return props.payload.code
  return 'unknown'
})
const errorMessage = computed(() => {
  if (props.payload?.kind === 'error') return props.payload.message
  return undefined
})
</script>

<template>
  <div class="chat-bubble-assistant" role="listitem" :class="{ 'chat-bubble-assistant--wide': isViz }">
    <div class="chat-bubble-assistant__bubble">
      <template v-if="isError">
        <MessageError
          :code="errorCode"
          :message="errorMessage"
          :message-id="messageId"
          @retry="(id: string) => emit('retry', id)"
        />
      </template>
      <template v-else-if="isViz && vizComponent">
        <ClientOnly v-if="isClientOnlyViz">
          <component :is="vizComponent" v-bind="(vizData as Record<string, unknown>)" />
        </ClientOnly>
        <component v-else :is="vizComponent" v-bind="(vizData as Record<string, unknown>)" />
      </template>
      <template v-else>
        <MessageMarkdown :content="content" :streaming="streaming" />
      </template>
    </div>
    <div v-if="hasMutation" class="chat-bubble-assistant__mutation" title="Profil mis à jour">
      <span aria-hidden="true">⟳</span>
      <span class="sr-only">Profil mis à jour</span>
    </div>
  </div>
</template>

<style scoped>
.chat-bubble-assistant {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
  margin: 0.5rem 0;
}
.chat-bubble-assistant__bubble {
  background: rgb(var(--color-bg-elevated, 255 255 255));
  border: 1px solid rgb(var(--color-border, 229 231 235));
  border-radius: 16px 16px 16px 4px;
  padding: 0.75rem 1rem;
  max-width: min(80ch, 75%);
  word-wrap: break-word;
}
.chat-bubble-assistant--wide .chat-bubble-assistant__bubble {
  max-width: min(720px, 95%);
}
.chat-bubble-assistant__mutation {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  border-radius: 50%;
  background: rgb(var(--color-success-100, 220 252 231));
  color: rgb(var(--color-success-700, 21 128 61));
  font-size: 0.875rem;
}
.sr-only {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0, 0, 0, 0);
  white-space: nowrap; border: 0;
}
</style>
