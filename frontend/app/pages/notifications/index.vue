<script setup lang="ts">
// F52 US1 — Centre des notifications.
import { computed, onMounted, ref } from 'vue'
import { useNotificationsStore } from '~/stores/notifications'
import { useNotificationsFilters } from '~/composables/useNotificationsFilters'
import NotificationFilters from '~/components/notifications/NotificationFilters.vue'
import NotificationList from '~/components/notifications/NotificationList.vue'
import NotificationDetailDrawer from '~/components/notifications/NotificationDetailDrawer.vue'

definePageMeta({
  layout: 'default',
  middleware: ['pme-only'],
  breadcrumb: [{ label: 'Notifications' }],
  title: 'Notifications',
})

const store = useNotificationsStore()
useNotificationsFilters(true)

const isMarkingAll = ref(false)
const errorMessage = ref<string | null>(null)
const drawerId = ref<string | null>(null)

const items = computed(() => store.filteredItems)
const hasFilters = computed(() => {
  const f = store.filters
  return f.unreadOnly || f.kinds.length > 0 || !!f.from || !!f.to
})
const drawerNotification = computed(() => {
  if (!drawerId.value) return null
  return store.items.find((n) => n.id === drawerId.value) ?? null
})

onMounted(async () => {
  await store.loadInitial()
})

function openDrawer(id: string) {
  drawerId.value = id
}
function closeDrawer() {
  drawerId.value = null
}

async function onMarkAll() {
  if (isMarkingAll.value) return
  isMarkingAll.value = true
  errorMessage.value = null
  try {
    await store.markAllReadOptimistic(
      store.filters.kinds.length > 0 ? store.filters.kinds : undefined
    )
  } catch {
    errorMessage.value = 'Échec du marquage. Réessayez.'
  } finally {
    isMarkingAll.value = false
  }
}
</script>

<template>
  <section class="mx-auto max-w-4xl p-4 sm:p-6">
    <header class="mb-4 flex items-start justify-between gap-3">
      <div>
        <h1 class="text-xl font-semibold text-gray-900 sm:text-2xl">Notifications</h1>
        <p class="text-sm text-gray-600">
          {{ store.unreadCount }} non-lue{{ store.unreadCount > 1 ? 's' : '' }}
        </p>
      </div>
      <button
        type="button"
        class="rounded bg-brand-600 px-3 py-2 text-sm font-medium text-white shadow hover:bg-brand-700 disabled:opacity-50"
        data-testid="mark-all-read-btn"
        :disabled="store.unreadCount === 0 || isMarkingAll"
        @click="onMarkAll"
      >
        {{ isMarkingAll ? 'En cours…' : 'Tout marquer comme lu' }}
      </button>
    </header>
    <div v-if="errorMessage" class="mb-3 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700" data-testid="mark-all-error">
      {{ errorMessage }}
    </div>
    <NotificationFilters class="mb-4" />
    <NotificationList :items="items" :has-filters="hasFilters" @open="openDrawer" />
    <NotificationDetailDrawer
      :notification="drawerNotification"
      @close="closeDrawer"
      @mark-read="(id) => store.markRead(id)"
    />
  </section>
</template>
