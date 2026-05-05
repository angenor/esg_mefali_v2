<script setup lang="ts">
// F38 T041 — TheBottomNav (mobile < 1024 px)
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const emit = defineEmits<{ 'open-more': [] }>()

const route = useRoute()

interface Item {
  id: string
  label: string
  to?: string
  action?: 'more'
  icon: string
}

const ITEMS: ReadonlyArray<Item> = [
  { id: 'chat', label: 'Chat', to: '/chat', icon: 'chat' },
  { id: 'dashboard', label: 'Tableau de bord', to: '/dashboard', icon: 'home' },
  { id: 'profil', label: 'Profil', to: '/profil', icon: 'user' },
  { id: 'more', label: 'Plus', action: 'more', icon: 'more' },
]

function isActive(item: Item): boolean {
  if (!item.to) return false
  if (item.to === '/dashboard') return route.path === '/dashboard'
  return route.path === item.to || route.path.startsWith(item.to + '/')
}

const baseBtn = computed(
  () =>
    'flex flex-1 flex-col items-center justify-center gap-1 text-[11px] font-medium ' +
    'min-w-[48px] min-h-[48px] focus:outline-none focus:ring-2 focus:ring-brand-500'
)
</script>

<template>
  <nav
    aria-label="Navigation rapide"
    class="lg:hidden fixed inset-x-0 bottom-0 z-30 flex h-14 border-t border-gray-200 bg-white pb-[env(safe-area-inset-bottom)]"
    data-testid="bottom-nav"
  >
    <template v-for="item in ITEMS" :key="item.id">
      <NuxtLink
        v-if="item.to"
        :to="item.to"
        :class="[baseBtn, isActive(item) ? 'text-brand-700' : 'text-gray-600']"
        :data-active="isActive(item) ? 'true' : 'false'"
        :data-testid="`bottom-nav-${item.id}`"
        :data-tour="item.id === 'chat' ? 'chat' : item.id === 'profil' ? 'profil' : undefined"
        :style="{ minWidth: '48px', minHeight: '48px' }"
      >
        <UiIcon :name="item.icon" class="w-5 h-5" />
        <span>{{ item.label }}</span>
      </NuxtLink>
      <button
        v-else
        type="button"
        :class="[baseBtn, 'text-gray-600']"
        :data-testid="`bottom-nav-${item.id}`"
        :style="{ minWidth: '48px', minHeight: '48px' }"
        @click="emit('open-more')"
      >
        <UiIcon :name="item.icon" class="w-5 h-5" />
        <span>{{ item.label }}</span>
      </button>
    </template>
  </nav>
</template>
