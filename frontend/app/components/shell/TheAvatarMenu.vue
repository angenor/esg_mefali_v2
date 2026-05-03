<script setup lang="ts">
// F38 T070 — TheAvatarMenu
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useAuthStore } from '~/stores/auth'

const auth = useAuthStore()

const isOpen = ref(false)
const buttonRef = ref<HTMLButtonElement | null>(null)
const popoverRef = ref<HTMLElement | null>(null)

const initials = computed(() => {
  const email = auth.user?.email ?? ''
  const part = email.split('@')[0] ?? ''
  return part.slice(0, 2).toUpperCase() || '·'
})

const displayName = computed(() => auth.user?.raison_sociale || auth.user?.email || '')

function toggle(): void {
  isOpen.value = !isOpen.value
}
function close(): void {
  isOpen.value = false
}

async function onLogout(): Promise<void> {
  close()
  await auth.logout()
}

function onDocClick(e: MouseEvent): void {
  if (!isOpen.value) return
  const target = e.target as Node | null
  if (!target) return
  if (popoverRef.value?.contains(target) || buttonRef.value?.contains(target)) return
  close()
}
function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape' && isOpen.value) {
    e.preventDefault()
    close()
    buttonRef.value?.focus()
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
</script>

<template>
  <div class="relative">
    <button
      ref="buttonRef"
      type="button"
      class="inline-flex h-9 w-9 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
      :aria-label="`Menu de l'utilisateur ${displayName}`"
      :aria-expanded="isOpen"
      data-testid="avatar-button"
      @click="toggle"
    >
      {{ initials }}
    </button>

    <div
      v-if="isOpen"
      ref="popoverRef"
      role="menu"
      class="absolute right-0 z-30 mt-2 w-64 overflow-hidden rounded-lg border border-gray-200 bg-white shadow-xl"
      data-testid="avatar-popover"
    >
      <div class="border-b border-gray-200 px-3 py-3">
        <p class="truncate text-sm font-semibold text-gray-900">{{ displayName }}</p>
        <p v-if="auth.user?.email" class="truncate text-xs text-gray-500">{{ auth.user.email }}</p>
      </div>
      <div class="border-b border-gray-200 px-3 py-2">
        <label for="lang-select" class="block text-xs font-medium text-gray-500">Langue</label>
        <select
          id="lang-select"
          disabled
          class="mt-1 w-full rounded border border-gray-200 bg-gray-50 px-2 py-1 text-sm text-gray-700"
          data-testid="avatar-lang-select"
        >
          <option value="fr" selected>Français</option>
          <option value="en" disabled>English (bientôt)</option>
        </select>
      </div>
      <ul class="py-1">
        <li>
          <NuxtLink
            to="/parametres"
            role="menuitem"
            class="block px-3 py-2 text-sm text-gray-800 hover:bg-gray-50"
            @click="close"
          >Mon compte</NuxtLink>
        </li>
        <li>
          <NuxtLink
            to="/parametres"
            role="menuitem"
            class="block px-3 py-2 text-sm text-gray-800 hover:bg-gray-50"
            @click="close"
          >Paramètres</NuxtLink>
        </li>
      </ul>
      <div class="border-t border-gray-200 py-1">
        <button
          type="button"
          role="menuitem"
          class="block w-full px-3 py-2 text-left text-sm text-red-700 hover:bg-red-50"
          data-testid="avatar-logout"
          @click="onLogout"
        >Déconnexion</button>
      </div>
    </div>
  </div>
</template>
