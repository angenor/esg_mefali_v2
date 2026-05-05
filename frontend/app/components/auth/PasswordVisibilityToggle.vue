<script setup lang="ts">
// F42 T023 — toggle œil pour show/hide password
import { useT } from "~/composables/useT"

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ (e: "update:visible", v: boolean): void }>()

const { t } = useT()

function toggle() {
  emit("update:visible", !props.visible)
}
</script>

<template>
  <button
    type="button"
    class="inline-flex items-center justify-center text-sm text-gray-600 hover:text-gray-900 px-2 py-1 rounded focus:outline-none focus:ring-2 focus:ring-brand-500"
    :aria-pressed="visible"
    :aria-label="visible ? t('auth.password.hide') : t('auth.password.show')"
    @click="toggle"
  >
    <svg v-if="!visible" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.477 0 8.268 2.943 9.542 7-1.274 4.057-5.065 7-9.542 7S3.732 16.057 2.458 12z" />
      <circle cx="12" cy="12" r="3" stroke-width="2" />
    </svg>
    <svg v-else class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3l18 18M10.584 10.587a3 3 0 104.243 4.243M9.88 4.65A9.96 9.96 0 0112 4.5c4.477 0 8.268 2.943 9.542 7a10.02 10.02 0 01-4.293 5.092M6.168 6.168A10.02 10.02 0 002.458 12c1.274 4.057 5.065 7 9.542 7 1.51 0 2.94-.286 4.243-.808" />
    </svg>
  </button>
</template>
