<script setup lang="ts">
// F49 T044 — Rendu lecture seule des KPI publiés sur /verify/[id].
//
// Chaque indicateur affiche label/label_en, value, unit et un repère cliquable
// vers la source correspondante dans `payload.sources`. Aucun élément d'édition.
import { computed } from "vue"
import { useVerifyI18n } from "~/composables/useVerifyI18n"
import type { PublicIndicator, PublicSource } from "~/types/attestations"

interface Props {
  indicators: PublicIndicator[]
  sources: PublicSource[]
  lang?: "fr" | "en"
}
const props = defineProps<Props>()
const { t, lang } = useVerifyI18n(props.lang)

const sourceById = computed<Record<string, PublicSource>>(() => {
  const out: Record<string, PublicSource> = {}
  for (const s of props.sources) out[s.id] = s
  return out
})

function indicatorLabel(i: PublicIndicator): string {
  if (lang.value === "en" && i.label_en) return i.label_en
  return i.label
}

function indicatorValue(i: PublicIndicator): string {
  if (i.value === null || i.value === undefined) return "—"
  const v = typeof i.value === "number" ? i.value.toString() : String(i.value)
  return i.unit ? `${v} ${i.unit}` : v
}

function sourceIndex(sourceId: string | null | undefined): number {
  if (!sourceId) return -1
  return props.sources.findIndex((s) => s.id === sourceId)
}
</script>

<template>
  <section class="space-y-6" data-testid="payload-view">
    <div>
      <h2 class="mb-3 text-lg font-semibold text-gray-900">
        {{ t("payload.indicators_title") }}
      </h2>
      <p
        v-if="indicators.length === 0"
        class="text-sm text-gray-500"
        data-testid="no-indicators"
      >
        {{ t("payload.no_indicators") }}
      </p>
      <ul v-else class="grid gap-3 sm:grid-cols-2" data-testid="indicators-list">
        <li
          v-for="i in indicators"
          :key="i.code"
          class="rounded-lg border border-gray-200 bg-white p-4"
          data-testid="indicator-item"
        >
          <p class="text-xs uppercase text-gray-500">{{ i.code }}</p>
          <p class="mt-1 text-sm font-medium text-gray-900">
            {{ indicatorLabel(i) }}
          </p>
          <p class="mt-2 text-2xl font-bold text-brand-700">
            {{ indicatorValue(i) }}
          </p>
          <p
            v-if="i.source_id && sourceById[i.source_id]"
            class="mt-2 text-xs text-gray-600"
          >
            <a
              :href="`#source-${i.source_id}`"
              class="inline-flex items-center gap-1 text-brand-600 hover:underline"
              data-testid="source-pin"
            >
              <span aria-hidden="true">📎</span>
              <span>
                source #{{ sourceIndex(i.source_id) + 1 }} —
                {{ sourceById[i.source_id]?.title }}
              </span>
            </a>
          </p>
        </li>
      </ul>
    </div>

    <div v-if="sources.length > 0">
      <h2 class="mb-3 text-lg font-semibold text-gray-900">
        {{ t("payload.sources_title") }}
      </h2>
      <ol class="list-decimal space-y-2 pl-6 text-sm text-gray-700">
        <li v-for="s in sources" :key="s.id" :id="`source-${s.id}`">
          <a
            v-if="s.url"
            :href="s.url"
            target="_blank"
            rel="noopener noreferrer"
            class="text-brand-600 hover:underline"
          >
            {{ s.title }}
          </a>
          <span v-else>{{ s.title }}</span>
        </li>
      </ol>
    </div>
  </section>
</template>
