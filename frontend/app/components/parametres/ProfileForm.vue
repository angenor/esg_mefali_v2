<script setup lang="ts">
// F52 US2 — Formulaire profil de base (lecture seule MVP).
import { computed } from 'vue'

interface Props {
  email: string
  emailPending?: string | null
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'change-email'): void
  (e: 'change-password'): void
}>()

const hasPending = computed(() => Boolean(props.emailPending))
</script>

<template>
  <section class="rounded-lg border border-gray-200 bg-white p-4">
    <h2 class="text-lg font-semibold text-gray-900">Informations personnelles</h2>
    <dl class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
      <div>
        <dt class="text-xs uppercase text-gray-500">E-mail</dt>
        <dd class="text-sm text-gray-900">{{ email }}</dd>
        <p
          v-if="hasPending"
          class="mt-1 text-xs text-amber-700"
          data-testid="profile-email-pending"
        >
          En attente de vérification : {{ emailPending }}
        </p>
      </div>
    </dl>
    <div class="mt-4 flex flex-wrap gap-2">
      <button
        type="button"
        class="rounded border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
        data-testid="profile-change-email"
        @click="emit('change-email')"
      >
        Modifier l'e-mail
      </button>
      <button
        type="button"
        class="rounded border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
        data-testid="profile-change-password"
        @click="emit('change-password')"
      >
        Changer le mot de passe
      </button>
    </div>
  </section>
</template>
