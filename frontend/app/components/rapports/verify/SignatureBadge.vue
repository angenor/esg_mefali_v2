<script setup lang="ts">
// F49 T042 — Badge signature ✓ vert / ✗ rouge pour /verify/[id].
import { computed, toRef } from "vue"
import { useVerifyI18n } from "~/composables/useVerifyI18n"

interface Props {
  valid: boolean
  lang?: "fr" | "en"
}
const props = defineProps<Props>()
const { t } = useVerifyI18n(toRef(props, "lang") as import("vue").Ref<import("~/composables/useVerifyI18n").VerifyLang>)

const label = computed(() =>
  props.valid ? t("badge.valid") : t("badge.invalid"),
)
</script>

<template>
  <div
    class="inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold"
    :class="
      valid
        ? 'bg-green-50 text-green-700 ring-1 ring-green-200'
        : 'bg-red-50 text-red-700 ring-1 ring-red-200'
    "
    role="status"
    :aria-label="label"
    data-testid="signature-badge"
    :data-valid="valid ? 'true' : 'false'"
  >
    <span aria-hidden="true" class="text-base leading-none">
      {{ valid ? "✓" : "✗" }}
    </span>
    <span>{{ label }}</span>
  </div>
</template>
