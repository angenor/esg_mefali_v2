<script setup lang="ts">
// F38 T060 — TheOfflineBanner
import { useOnlineStatus } from '~/composables/useOnlineStatus'

const { isOnline } = useOnlineStatus()
</script>

<template>
  <div
    v-if="!isOnline"
    role="status"
    aria-live="polite"
    class="fixed inset-x-0 top-0 z-[1100] flex h-7 items-center justify-center bg-amber-100 px-3 text-xs text-amber-900"
    data-testid="offline-banner"
  >
    Connexion perdue. Vos modifications ne seront pas enregistrées tant que la
    connexion n'est pas rétablie.
  </div>
</template>
