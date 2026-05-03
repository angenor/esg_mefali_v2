<script setup lang="ts">
// F38 T022 / T036 / T038 / T042 / T063 / T065 — Layout default (PME)
import { ref, onMounted, onBeforeUnmount, computed, defineAsyncComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TheSidebar from '~/components/shell/TheSidebar.vue'
import TheHeader from '~/components/shell/TheHeader.vue'
import TheBottomNav from '~/components/shell/TheBottomNav.vue'
import TheNotificationsBell from '~/components/shell/TheNotificationsBell.vue'
import TheAvatarMenu from '~/components/shell/TheAvatarMenu.vue'
import TheBreadcrumbs from '~/components/shell/TheBreadcrumbs.vue'
import TheErrorBoundary from '~/components/shell/TheErrorBoundary.vue'
import { NAV_ITEMS } from '~/utils/shell-nav'
import { useCommandPalette } from '~/composables/useCommandPalette'
import { useNotificationsStream } from '~/composables/useNotificationsStream'
import { useAuthStore } from '~/stores/auth'

const TheCommandPalette = defineAsyncComponent(
  () => import('~/components/shell/TheCommandPalette.vue')
)
const TheBottomNavMore = defineAsyncComponent(
  () => import('~/components/shell/TheBottomNavMore.vue')
)

const collapsed = ref(false)
const route = useRoute()
const router = useRouter()

const pageTitle = computed(() => (route.meta.title as string | undefined) ?? 'ESG Mefali')
useHead({
  title: pageTitle,
  titleTemplate: (t?: string) =>
    t && t !== 'ESG Mefali' ? `${t} — ESG Mefali` : 'ESG Mefali',
})

const notif = useNotificationsStore()
const stream = useNotificationsStream()

// Drawer mobile (US4)
const drawerOpen = ref(false)
const moreSheetOpen = ref(false)

function openDrawer(): void {
  drawerOpen.value = true
}
function closeDrawer(): void {
  drawerOpen.value = false
}

router.afterEach(() => {
  if (drawerOpen.value) closeDrawer()
  if (moreSheetOpen.value) moreSheetOpen.value = false
})

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape' && drawerOpen.value) {
    closeDrawer()
  }
}

// Palette : registre par défaut (T036)
const palette = useCommandPalette()
palette.registerActions([
  ...NAV_ITEMS.map((item) => ({
    id: `nav.${item.id}`,
    label: `Aller à ${item.label.toLowerCase()}`,
    route: item.to,
    group: 'Navigation' as const,
    keywords: [item.label],
  })),
  {
    id: 'nav.notifications',
    label: 'Voir les notifications',
    route: '/notifications',
    group: 'Navigation',
  },
  {
    id: 'action.logout',
    label: 'Se déconnecter',
    run: () => useAuthStore().logout(),
    group: 'Actions',
  },
  {
    id: 'action.toggle-sidebar',
    label: 'Afficher / masquer la barre latérale',
    run: () => {
      collapsed.value = !collapsed.value
    },
    group: 'Actions',
  },
  {
    id: 'help.shortcuts',
    label: 'Voir les raccourcis clavier',
    route: '/parametres#raccourcis',
    group: 'Aide',
  },
])

onMounted(() => {
  void notif.loadInitial()
  stream.start()
  if (typeof document !== 'undefined') {
    document.addEventListener('keydown', onKeydown)
  }
})

onBeforeUnmount(() => {
  stream.stop()
  if (typeof document !== 'undefined') {
    document.removeEventListener('keydown', onKeydown)
  }
})
</script>

<template>
  <div class="flex h-screen bg-gray-50">
    <TheSidebar v-model:collapsed="collapsed" />

    <!-- Drawer mobile (US4) -->
    <Transition name="drawer">
      <div
        v-if="drawerOpen"
        class="fixed inset-0 z-40 lg:hidden"
        data-testid="drawer-overlay"
        @click.self="closeDrawer"
      >
        <div class="absolute inset-0 bg-black/40" />
        <aside
          class="absolute left-0 top-0 h-full w-[280px] bg-white shadow-xl"
          role="dialog"
          aria-modal="true"
          aria-label="Navigation principale"
          data-testid="drawer-panel"
        >
          <div class="flex h-14 items-center justify-between border-b border-gray-200 px-4">
            <span class="text-lg font-bold text-brand-600">ESG Mefali</span>
            <button
              type="button"
              class="rounded p-1 text-gray-500 hover:bg-gray-100"
              aria-label="Fermer le menu"
              @click="closeDrawer"
            >
              ✕
            </button>
          </div>
          <nav aria-label="Navigation principale" class="overflow-y-auto py-2">
            <ul class="space-y-1 px-2">
              <li v-for="item in NAV_ITEMS" :key="item.id">
                <NuxtLink
                  :to="item.to"
                  :class="[
                    'flex items-center gap-3 rounded-md px-2 py-2 text-sm font-medium',
                    route.path.startsWith(item.to)
                      ? 'bg-brand-50 text-brand-700'
                      : 'text-gray-700 hover:bg-gray-100',
                  ]"
                >
                  {{ item.label }}
                </NuxtLink>
              </li>
            </ul>
          </nav>
        </aside>
      </div>
    </Transition>

    <div class="flex min-w-0 flex-1 flex-col">
      <TheHeader @toggle-drawer="openDrawer">
        <template #breadcrumbs>
          <TheBreadcrumbs />
        </template>
        <template #bell>
          <TheNotificationsBell />
        </template>
        <template #avatar>
          <TheAvatarMenu />
        </template>
      </TheHeader>
      <main class="flex-1 overflow-y-auto pb-14 lg:pb-0" data-testid="main-content">
        <NuxtErrorBoundary>
          <slot />
          <template #error="{ error, clearError }">
            <TheErrorBoundary
              :error="error as Error"
              @reload="clearError({ redirect: route.fullPath })"
            />
          </template>
        </NuxtErrorBoundary>
      </main>
      <TheBottomNav @open-more="moreSheetOpen = true" />
    </div>

    <ClientOnly>
      <TheCommandPalette />
      <TheBottomNavMore v-if="moreSheetOpen" @close="moreSheetOpen = false" />
    </ClientOnly>
  </div>
</template>

<style scoped>
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.15s ease;
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
</style>
