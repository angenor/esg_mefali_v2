<script setup lang="ts">
// F52 US1 — Ligne de notification.
import { computed } from 'vue'
import type { Notification, NotificationKind } from '~/stores/notifications'

interface Props {
  notification: Notification
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'open', id: string): void
}>()

const kindLabels: Record<NotificationKind, string> = {
  deadline_j_minus_30: 'Échéance J-30',
  deadline_j_minus_7: 'Échéance J-7',
  deadline_j_minus_1: 'Échéance J-1',
  candidature_inactive: 'Candidature inactive',
  offre_recommandee: 'Offre recommandée',
  system: 'Système',
}

const formattedDate = computed(() => {
  try {
    return new Date(props.notification.created_at).toLocaleString('fr-FR', {
      dateStyle: 'short',
      timeStyle: 'short',
    })
  } catch {
    return props.notification.created_at
  }
})

const isUnread = computed(() => !props.notification.read_at)
</script>

<template>
  <li
    class="flex cursor-pointer items-start gap-3 px-4 py-3 transition hover:bg-gray-50"
    :class="{ 'bg-brand-50/60': isUnread }"
    :data-testid="`notif-row-${notification.id}`"
    @click="emit('open', notification.id)"
  >
    <span
      class="mt-1 inline-block h-2.5 w-2.5 flex-none rounded-full"
      :class="isUnread ? 'bg-brand-600' : 'bg-transparent'"
      aria-hidden="true"
    />
    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2">
        <span class="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium uppercase text-gray-700">
          {{ kindLabels[notification.kind] }}
        </span>
        <span class="text-xs text-gray-500">{{ formattedDate }}</span>
      </div>
      <p class="mt-0.5 text-sm font-medium text-gray-900">{{ notification.title }}</p>
      <p v-if="notification.body" class="truncate text-xs text-gray-500">
        {{ notification.body }}
      </p>
    </div>
  </li>
</template>
