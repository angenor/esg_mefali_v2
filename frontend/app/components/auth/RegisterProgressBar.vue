<script setup lang="ts">
// F42 T024 — Barre de progression wizard register
import { computed } from "vue"
import { useT } from "~/composables/useT"

const props = defineProps<{ step: number; total: number }>()
const { t } = useT()

const segments = computed(() =>
  Array.from({ length: props.total }, (_, i) => i < props.step),
)
</script>

<template>
  <div class="space-y-2" data-testid="register-progress">
    <div class="flex gap-1.5" :aria-label="t('auth.register.progress', { step, total })">
      <div
        v-for="(active, i) in segments"
        :key="i"
        class="h-1.5 flex-1 rounded-full"
        :class="active ? 'bg-brand-600' : 'bg-gray-200'"
      />
    </div>
    <p class="text-xs text-gray-600">
      {{ t("auth.register.progress", { step, total }) }}
    </p>
  </div>
</template>
