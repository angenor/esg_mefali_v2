<script setup lang="ts">
// F38 T059 — TheNotificationsBell (cloche + popover)
import { computed, ref, onMounted, onBeforeUnmount, nextTick } from 'vue'

const notif = useNotificationsStore()

const isOpen = ref(false)
const buttonRef = ref<HTMLButtonElement | null>(null)
const popoverRef = ref<HTMLElement | null>(null)

const unreadCount = computed(() => notif.unreadCount)
const latest = computed(() => notif.latestUnread)

function toggle(): void {
  isOpen.value = !isOpen.value
}

async function close(): Promise<void> {
  isOpen.value = false
  await nextTick()
  buttonRef.value?.focus()
}

async function onClickNotif(id: string, link?: string): Promise<void> {
  await notif.markRead(id)
  if (link) await navigateTo(link)
  await close()
}

function onDocClick(e: MouseEvent): void {
  if (!isOpen.value) return
  const target = e.target as Node | null
  if (!target) return
  if (popoverRef.value?.contains(target) || buttonRef.value?.contains(target)) return
  isOpen.value = false
}
function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape' && isOpen.value) {
    e.preventDefault()
    void close()
  }
}

onMounted(() => {
  if (typeof document === 'undefined') return
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  if (typeof document === 'undefined') return
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKeydown)
})

const badgeLabel = computed(() => (unreadCount.value > 99 ? '99+' : String(unreadCount.value)))
</script>

<template>
  <div class="relative">
    <button
      ref="buttonRef"
      type="button"
      class="relative rounded p-2 text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
      :aria-label="`Notifications, ${unreadCount} non lues`"
      :aria-expanded="isOpen"
      data-testid="bell-button"
      @click="toggle"
    >
      <span aria-hidden="true">🔔</span>
      <span
        v-if="unreadCount > 0"
        class="absolute -right-0.5 -top-0.5 inline-flex min-w-[18px] items-center justify-center rounded-full bg-brand-600 px-1 text-[10px] font-medium text-white"
        data-testid="bell-badge"
      >{{ badgeLabel }}</span>
    </button>

    <div
      v-if="isOpen"
      ref="popoverRef"
      role="dialog"
      aria-label="Notifications"
      class="absolute right-0 z-30 mt-2 w-80 overflow-hidden rounded-lg border border-gray-200 bg-white shadow-xl"
      data-testid="bell-popover"
    >
      <div class="border-b border-gray-200 px-3 py-2 text-sm font-semibold text-gray-900">
        Notifications
      </div>
      <ul v-if="latest.length > 0" class="max-h-72 divide-y divide-gray-100 overflow-y-auto">
        <li v-for="n in latest" :key="n.id">
          <button
            type="button"
            class="block w-full px-3 py-2 text-left text-sm hover:bg-gray-50"
            :data-testid="`bell-item-${n.id}`"
            @click="onClickNotif(n.id, n.link)"
          >
            <span class="block font-medium text-gray-900">{{ n.title }}</span>
            <span v-if="n.body" class="block truncate text-xs text-gray-500">{{ n.body }}</span>
          </button>
        </li>
      </ul>
      <p v-else class="px-3 py-4 text-center text-sm text-gray-500">
        Aucune notification non lue.
      </p>
      <NuxtLink
        to="/notifications"
        class="block border-t border-gray-200 px-3 py-2 text-center text-sm font-medium text-brand-700 hover:bg-gray-50"
        @click="close()"
      >
        Voir toutes les notifications
      </NuxtLink>
    </div>
  </div>
</template>
