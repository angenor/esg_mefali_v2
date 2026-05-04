<!--
  F48 US10 (P2) — ExportPdfButton
  Placeholder désactivé MVP avec infobulle « À venir — F51 ».
-->
<script setup lang="ts">
import { useT } from '~/composables/useT'

const { t } = useT()
</script>

<template>
  <button
    type="button"
    class="inline-flex cursor-not-allowed items-center gap-2 rounded-md bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-500 ring-1 ring-slate-200"
    :disabled="true"
    :title="t('credit_score.export.coming_soon')"
    :aria-disabled="true"
    data-testid="export-pdf-button"
  >
    <svg
      class="h-4 w-4"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M12 10v6m0 0l-3-3m3 3l3-3M4 6h16M4 18h16"
      />
    </svg>
    {{ t('credit_score.export.button') }}
    <span
      class="ml-1 rounded-full bg-slate-200 px-1.5 py-0.5 text-xs font-medium text-slate-600"
      aria-hidden="true"
    >{{ t('credit_score.export.badge_soon') }}</span>
  </button>
</template>
