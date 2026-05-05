<script setup lang="ts">
// F52 US1 — Drawer de détail d'une notification.
import { computed } from 'vue'
import type { Notification, NotificationKind } from '~/stores/notifications'

interface Props {
  notification: Notification | null
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'mark-read', id: string): void
}>()

const open = computed(() => props.notification !== null)

const kindLabels: Record<NotificationKind, string> = {
  deadline_j_minus_30: 'Échéance J-30',
  deadline_j_minus_7: 'Échéance J-7',
  deadline_j_minus_1: 'Échéance J-1',
  candidature_inactive: 'Candidature inactive',
  offre_recommandee: 'Offre recommandée',
  system: 'Système',
}

function onMarkRead() {
  if (props.notification) emit('mark-read', props.notification.id)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="drawer">
      <aside
        v-if="open && notification"
        role="dialog"
        aria-label="Détail notification"
        class="fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col bg-white shadow-2xl"
        data-testid="notif-drawer"
      >
        <header class="flex items-start justify-between gap-3 border-b border-gray-200 px-5 py-4">
          <div class="min-w-0">
            <span class="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium uppercase text-gray-700">
              {{ kindLabels[notification.kind] }}
            </span>
            <h2 class="mt-1 truncate text-base font-semibold text-gray-900">{{ notification.title }}</h2>
          </div>
          <button
            type="button"
            class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Fermer"
            data-testid="notif-drawer-close"
            @click="emit('close')"
          >
            <span aria-hidden>×</span>
          </button>
        </header>
        <section class="flex-1 overflow-y-auto px-5 py-4 text-sm text-gray-700">
          <p v-if="notification.body" class="whitespace-pre-line">{{ notification.body }}</p>
          <p v-else class="italic text-gray-500">Aucune description supplémentaire.</p>
          <NuxtLink
            v-if="notification.link"
            :to="notification.link"
            class="mt-4 inline-block text-sm font-medium text-brand-700 hover:underline"
            data-testid="notif-drawer-link"
          >
            Voir le détail →
          </NuxtLink>
        </section>
        <footer class="flex items-center justify-end gap-2 border-t border-gray-200 px-5 py-3">
          <button
            v-if="!notification.read_at"
            type="button"
            class="rounded bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
            data-testid="notif-drawer-mark-read"
            @click="onMarkRead"
          >
            Marquer comme lue
          </button>
          <button
            type="button"
            class="rounded border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            @click="emit('close')"
          >
            Fermer
          </button>
        </footer>
      </aside>
    </Transition>
  </Teleport>
</template>

<style scoped>
.drawer-enter-active,
.drawer-leave-active {
  transition: transform 200ms ease;
}
.drawer-enter-from,
.drawer-leave-to {
  transform: translateX(100%);
}
</style>
