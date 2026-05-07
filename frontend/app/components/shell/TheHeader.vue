<script setup lang="ts">
// F38 T021 — TheHeader (raison sociale + slots cloche/avatar/breadcrumbs)
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useAuthStore } from '~/stores/auth'

const emit = defineEmits<{ 'toggle-drawer': [] }>()

const auth = useAuthStore()
const displayName = computed(() => {
  if (!auth.user) return ''
  return auth.user.raison_sociale || auth.user.email
})

const isMobile = ref(false)

function handleResize() {
  if (typeof window === 'undefined') return
  isMobile.value = window.matchMedia('(max-width: 1023.98px)').matches
}

onMounted(() => {
  if (typeof window === 'undefined') return
  handleResize()
  const mql = window.matchMedia('(max-width: 1023.98px)')
  if (mql.addEventListener) {
    mql.addEventListener('change', handleResize)
  }
  onBeforeUnmount(() => {
    if (mql.removeEventListener) mql.removeEventListener('change', handleResize)
  })
})
</script>

<template>
  <header
    class="h-14 flex items-center gap-3 border-b border-gray-200 bg-white px-4"
    data-testid="the-header"
    style="height: 56px;"
  >
    <button
      v-if="isMobile"
      type="button"
      class="rounded p-2 text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
      aria-label="Ouvrir le menu de navigation"
      data-testid="header-hamburger"
      @click="emit('toggle-drawer')"
    >
      <span aria-hidden="true">☰</span>
    </button>

    <div class="font-semibold text-gray-900 truncate" data-testid="header-tenant">
      <!--
        Identique à TheAvatarMenu : ``auth.user`` n'est dispo qu'après
        hydratation client (cookies httpOnly). On force le rendu CSR
        uniquement pour éviter un hydration mismatch (SSR rend "" / CSR
        rend l'email ou la raison sociale).
      -->
      <ClientOnly>
        {{ displayName }}
      </ClientOnly>
    </div>

    <div class="hidden md:block flex-1 min-w-0">
      <slot name="breadcrumbs" />
    </div>

    <div class="ml-auto flex items-center gap-2">
      <slot name="actions" />
      <slot name="bell" />
      <slot name="avatar" />
    </div>
  </header>
</template>
