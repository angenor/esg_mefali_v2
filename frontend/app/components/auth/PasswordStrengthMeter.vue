<script setup lang="ts">
// F42 T022 — Indicateur de robustesse mot de passe (4 segments + a11y)
import { computed, toRefs, watch } from "vue"
import { usePasswordStrength, type PasswordStrengthResult } from "~/composables/usePasswordStrength"
import { useT } from "~/composables/useT"

const props = defineProps<{ password: string }>()
const emit = defineEmits<{ (e: "change", v: PasswordStrengthResult): void }>()

const { t } = useT()
const { password } = toRefs(props)
const result = usePasswordStrength(password)

watch(result, (v) => emit("change", v), { immediate: true })

const segments = computed(() => {
  const s = result.value.score
  return [0, 1, 2, 3].map((i) => i < s)
})

const colorClass = computed(() => {
  switch (result.value.score) {
    case 0:
    case 1:
      return "bg-red-500"
    case 2:
      return "bg-amber-500"
    case 3:
      return "bg-emerald-500"
    case 4:
      return "bg-emerald-600"
    default:
      return "bg-gray-200"
  }
})

const labelKey = computed<
  | "auth.password.strength.0"
  | "auth.password.strength.1"
  | "auth.password.strength.2"
  | "auth.password.strength.3"
  | "auth.password.strength.4"
>(() => {
  const score = result.value.score
  return `auth.password.strength.${score}` as const
})
</script>

<template>
  <div class="space-y-2">
    <div
      class="grid grid-cols-4 gap-1.5"
      :aria-label="t('auth.password.aria.meter')"
      role="img"
    >
      <div
        v-for="(filled, i) in segments"
        :key="i"
        class="h-1.5 rounded-full transition-colors"
        :class="filled ? colorClass : 'bg-gray-200'"
      />
    </div>
    <div role="status" aria-live="polite" class="text-xs text-gray-700">
      {{ t(labelKey) }}
    </div>
    <ul class="text-xs text-gray-600 space-y-0.5">
      <li :class="result.criteria.length12 ? 'text-emerald-600' : 'text-gray-500'">
        {{ result.criteria.length12 ? "✓" : "•" }} {{ t("auth.password.criteria.length") }}
      </li>
      <li :class="result.criteria.uppercase ? 'text-emerald-600' : 'text-gray-500'">
        {{ result.criteria.uppercase ? "✓" : "•" }} {{ t("auth.password.criteria.uppercase") }}
      </li>
      <li :class="result.criteria.digit ? 'text-emerald-600' : 'text-gray-500'">
        {{ result.criteria.digit ? "✓" : "•" }} {{ t("auth.password.criteria.digit") }}
      </li>
      <li :class="result.criteria.symbol ? 'text-emerald-600' : 'text-gray-500'">
        {{ result.criteria.symbol ? "✓" : "•" }} {{ t("auth.password.criteria.symbol") }}
      </li>
    </ul>
  </div>
</template>
