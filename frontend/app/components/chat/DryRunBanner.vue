<template>
  <div
    v-if="active"
    class="dry-run-banner sticky top-0 z-30 bg-yellow-50 border-l-4 border-yellow-400 p-3 text-yellow-900 text-sm shadow-sm"
    role="status"
    aria-live="polite"
  >
    <span class="font-semibold mr-2">Mode simulation actif</span>
    <span>Les mutations ne sont pas appliquées en base. Aucune ligne d'audit n'est écrite.</span>
  </div>
</template>

<script setup lang="ts">
/**
 * DryRunBanner — bandeau jaune affiché quand l'admin a activé le mode dry_run
 * (US6, F55). Le store chat met à jour `dryRunActive` quand un event SSE
 * préfixé `dry_run:` est reçu.
 */
import { computed } from 'vue'
import { useChatStore } from '~/stores/chat'

const store = useChatStore()
const active = computed(() => store.dryRunActive === true)
</script>

<style scoped>
.dry-run-banner {
  font-family: inherit;
}
</style>
