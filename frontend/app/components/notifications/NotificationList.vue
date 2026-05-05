<script setup lang="ts">
// F52 US1 — Liste paginée des notifications (table avec NotificationRow).
import { computed } from 'vue'
import type { Notification } from '~/stores/notifications'
import NotificationRow from './NotificationRow.vue'
import NotificationsEmptyState from './NotificationsEmptyState.vue'

interface Props {
  items: Notification[]
  hasFilters?: boolean
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'open', id: string): void
}>()

const isEmpty = computed(() => props.items.length === 0)
</script>

<template>
  <NotificationsEmptyState v-if="isEmpty" :has-filters="hasFilters" />
  <ul
    v-else
    class="divide-y divide-gray-100 overflow-hidden rounded-lg border border-gray-200 bg-white"
    aria-label="Liste des notifications"
    data-testid="notifications-list"
  >
    <NotificationRow
      v-for="n in items"
      :key="n.id"
      :notification="n"
      @open="(id) => emit('open', id)"
    />
  </ul>
</template>
