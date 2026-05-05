<script setup lang="ts">
// F49 T043 — Bandeau rouge above-the-fold sur /verify/[id] si attestation révoquée.
import { computed } from "vue"
import { useVerifyI18n } from "~/composables/useVerifyI18n"
import type { RevokeReason } from "~/types/attestations"

interface Props {
  revokedAt: string | null
  reason: RevokeReason | null
  lang?: "fr" | "en"
}
const props = defineProps<Props>()
const { t, dateFormatter } = useVerifyI18n(props.lang)

const reasonLabel = computed(() => {
  if (!props.reason) return ""
  return t(`revoke_reason.${props.reason}`)
})

const dateLabel = computed(() => {
  if (!props.revokedAt) return ""
  return t("revoked_banner.revoked_at", {
    date: dateFormatter.value(props.revokedAt),
  })
})
</script>

<template>
  <div
    v-if="revokedAt"
    role="alert"
    class="border-2 border-red-300 bg-red-50 p-4 text-red-900"
    data-testid="revoked-banner"
  >
    <p class="text-lg font-bold uppercase tracking-wide">
      {{ t("revoked_banner.title") }}
    </p>
    <p class="mt-1 text-sm">{{ dateLabel }}</p>
    <p v-if="reason" class="mt-1 text-sm">
      <span class="font-semibold">{{ t("revoked_banner.reason_label") }} :</span>
      {{ reasonLabel }}
    </p>
  </div>
</template>
