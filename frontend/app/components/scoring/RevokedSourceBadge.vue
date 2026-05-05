<script setup lang="ts">
// F46 T027 [US1] — Badge de source révoquée.
// Cf. specs/046-scoring-esg-ui/contracts/frontend-components.md §RevokedSourceBadge.
import UiBadge from "~/components/ui/UiBadge.vue"
import UiTooltip from "~/components/ui/UiTooltip.vue"
import { useT } from "~/composables/useT"

interface Props {
  sourceId: string
}

defineProps<Props>()

const { t } = useT()
const message = t("scoring.errors.revokedSource")
</script>

<template>
  <UiTooltip placement="top">
    <UiBadge
      severity="warning"
      variant="subtle"
      :aria-label="message"
      data-testid="revoked-source-badge"
      role="status"
    >
      <span aria-hidden="true">⚠</span>
      <span class="rs-badge__text">{{ t("scoring.status.missing") }}</span>
    </UiBadge>
    <template #content>{{ message }}</template>
  </UiTooltip>
</template>

<style scoped>
.rs-badge__text {
  margin-left: 0.25rem;
}
</style>
