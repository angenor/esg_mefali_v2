<!--
  F48 US1 — ClassificationLabel
  Affiche le libellé textuel + l'icône + la couleur de la classification.
  Le texte reste TOUJOURS visible (FR-015 / R-10 — daltonien-friendly).
-->
<script setup lang="ts">
import { computed } from 'vue'
import type { ClassificationView } from '~/types/creditScore'

interface Props {
  classification: ClassificationView
  size?: 'sm' | 'md' | 'lg'
}

const props = withDefaults(defineProps<Props>(), { size: 'md' })

const colorClasses = computed<string>(() => {
  switch (props.classification.colorToken) {
    case 'danger':
      return 'bg-red-50 text-red-700 ring-red-200'
    case 'warning':
      return 'bg-amber-50 text-amber-700 ring-amber-200'
    case 'success':
      return 'bg-emerald-50 text-emerald-700 ring-emerald-200'
    case 'success-strong':
      return 'bg-green-100 text-green-800 ring-green-300'
    default:
      return 'bg-slate-50 text-slate-700 ring-slate-200'
  }
})

const sizeClasses = computed<string>(() => {
  switch (props.size) {
    case 'sm':
      return 'px-2 py-0.5 text-xs gap-1'
    case 'lg':
      return 'px-4 py-2 text-base gap-2'
    default:
      return 'px-3 py-1 text-sm gap-1.5'
  }
})

const iconPath = computed<string>(() => {
  switch (props.classification.bucket) {
    case 'excellent':
      return 'M5 13l4 4L19 7'
    case 'bon':
      return 'M5 12h14M12 5l7 7-7 7'
    case 'a_ameliorer':
      return 'M12 9v4m0 4h.01M5 19h14a2 2 0 002-2L13 5a2 2 0 00-2 0L3 17a2 2 0 002 2z'
    case 'insuffisant':
    default:
      return 'M6 18L18 6M6 6l12 12'
  }
})
</script>

<template>
  <span
    :class="[
      'inline-flex items-center rounded-full font-medium ring-1',
      colorClasses,
      sizeClasses,
    ]"
    :aria-label="`Classification : ${classification.label}`"
    role="status"
  >
    <svg
      class="h-4 w-4 shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        :d="iconPath"
      />
    </svg>
    <span>{{ classification.label }}</span>
  </span>
</template>
