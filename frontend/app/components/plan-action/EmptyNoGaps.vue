<script setup lang="ts">
// F45 T058 — Empty state : scoring complet sans gap exploitable.
import UiEmptyState from "~/components/ui/UiEmptyState.vue"
import { useT } from "~/composables/useT"

const { t } = useT()
</script>

<template>
  <UiEmptyState
    severity="success"
    :title="t('planAction.empty.noGaps.title')"
    :description="t('planAction.empty.noGaps.body')"
  />
</template>
