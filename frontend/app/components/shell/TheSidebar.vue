<script setup lang="ts">
// F38 T020 — TheSidebar (rail + déplié)
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { NAV_ITEMS } from '~/utils/shell-nav'

interface Props {
  collapsed?: boolean
}
const props = withDefaults(defineProps<Props>(), { collapsed: false })
const emit = defineEmits<{ 'update:collapsed': [value: boolean] }>()

const route = useRoute()
const notif = useNotificationsStore()
const unreadCount = computed(() => notif.unreadCount)

function isActive(to: string): boolean {
  if (to === '/dashboard') return route.path === '/dashboard'
  return route.path === to || route.path.startsWith(to + '/')
}

function badgeFor(key?: string): number {
  if (key === 'unread') return unreadCount.value
  return 0
}

const STORAGE_KEY = 'shell.sidebar.collapsed'

onMounted(() => {
  if (typeof window === 'undefined') return
  const raw = window.localStorage.getItem(STORAGE_KEY)
  if (raw === '1' && !props.collapsed) emit('update:collapsed', true)
  if (raw === '0' && props.collapsed) emit('update:collapsed', false)
})

watch(
  () => props.collapsed,
  (val) => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(STORAGE_KEY, val ? '1' : '0')
  }
)

function toggle() {
  emit('update:collapsed', !props.collapsed)
}
</script>

<template>
  <aside
    :class="[
      'hidden lg:flex flex-col border-r border-gray-200 bg-white transition-[width] duration-150',
      props.collapsed ? 'w-16' : 'w-64',
    ]"
    data-testid="the-sidebar"
  >
    <div class="h-14 flex items-center px-4 border-b border-gray-200">
      <span v-if="!props.collapsed" class="text-lg font-bold text-brand-600">ESG Mefali</span>
      <button
        type="button"
        class="ml-auto rounded p-1 text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
        :aria-label="props.collapsed ? 'Déplier la barre latérale' : 'Replier la barre latérale'"
        :aria-expanded="!props.collapsed"
        @click="toggle"
      >
        <span aria-hidden="true">{{ props.collapsed ? '›' : '‹' }}</span>
      </button>
    </div>

    <nav aria-label="Navigation principale" class="flex-1 overflow-y-auto py-2">
      <ul class="space-y-1 px-2">
        <li v-for="item in NAV_ITEMS" :key="item.id">
          <NuxtLink
            :to="item.to"
            :data-active="isActive(item.to) ? 'true' : 'false'"
            :class="[
              'group flex items-center rounded-md px-2 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-brand-500',
              isActive(item.to)
                ? 'bg-brand-50 text-brand-700'
                : 'text-gray-700 hover:bg-gray-100',
              props.collapsed ? 'justify-center' : 'gap-3',
            ]"
          >
            <span
              :class="['inline-block w-5 h-5 shrink-0', `i-shell-${item.icon}`]"
              aria-hidden="true"
            />
            <span v-if="!props.collapsed" class="truncate">{{ item.label }}</span>
            <UiTooltip v-else :label="item.label" />
            <UiBadge
              v-if="!props.collapsed && item.badgeKey === 'unread' && badgeFor(item.badgeKey) > 0"
              severity="info"
              class="ml-auto"
            >
              {{ badgeFor(item.badgeKey) > 99 ? '99+' : badgeFor(item.badgeKey) }}
            </UiBadge>
          </NuxtLink>
        </li>
        <li>
          <NuxtLink
            to="/notifications"
            :data-active="isActive('/notifications') ? 'true' : 'false'"
            :class="[
              'group flex items-center rounded-md px-2 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-brand-500',
              isActive('/notifications')
                ? 'bg-brand-50 text-brand-700'
                : 'text-gray-700 hover:bg-gray-100',
              props.collapsed ? 'justify-center' : 'gap-3',
            ]"
            data-testid="nav-notifications"
          >
            <span class="inline-block w-5 h-5 shrink-0 i-shell-bell" aria-hidden="true" />
            <span v-if="!props.collapsed" class="truncate">Notifications</span>
            <UiBadge
              v-if="!props.collapsed && unreadCount > 0"
              severity="info"
              class="ml-auto"
              data-testid="sidebar-unread-badge"
            >
              {{ unreadCount > 99 ? '99+' : unreadCount }}
            </UiBadge>
          </NuxtLink>
        </li>
      </ul>
    </nav>
  </aside>
</template>
