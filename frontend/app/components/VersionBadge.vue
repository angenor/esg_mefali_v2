<script setup lang="ts">
// F04 — VersionBadge SFC (T113, US7). Displays the active référentiel pin.
import { computed } from 'vue';
import { formatVersionBadge } from '../composables/useVersionBadge';

const props = defineProps<{
  referentielName: string;
  version: number;
  validFrom: string;
}>();

const label = computed(() =>
  formatVersionBadge(props.referentielName, props.version, props.validFrom),
);
</script>

<template>
  <span class="version-badge" :title="label">{{ label }}</span>
</template>

<style scoped>
.version-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  font-size: 0.85rem;
  border-radius: 0.5rem;
  background: #f1f5f9;
  color: #1e293b;
}
</style>
