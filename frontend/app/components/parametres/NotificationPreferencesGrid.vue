<script setup lang="ts">
// F52 US2 — Matrice de toggles préférences notifications.
import { onMounted } from 'vue'
import { useNotificationPreferencesStore } from '~/stores/notificationPreferences'
import type { NotificationKind } from '~/stores/notifications'
import type { NotificationChannel } from '~/stores/notificationPreferences'

const store = useNotificationPreferencesStore()

const KINDS: { value: NotificationKind; label: string }[] = [
  { value: 'deadline_j_minus_30', label: 'Échéance J-30' },
  { value: 'deadline_j_minus_7', label: 'Échéance J-7' },
  { value: 'deadline_j_minus_1', label: 'Échéance J-1' },
  { value: 'candidature_inactive', label: 'Candidature inactive' },
  { value: 'offre_recommandee', label: 'Offre recommandée' },
]
const CHANNELS: { value: NotificationChannel; label: string }[] = [
  { value: 'email', label: 'E-mail' },
  { value: 'in_app', label: 'In-app' },
]

onMounted(async () => {
  await store.load()
})

function toggle(kind: NotificationKind, channel: NotificationChannel, enabled: boolean) {
  store.togglePreference(kind, channel, enabled)
}
</script>

<template>
  <section class="rounded-lg border border-gray-200 bg-white p-4">
    <h2 class="text-lg font-semibold text-gray-900">Préférences de notifications</h2>
    <p class="mt-1 text-xs text-gray-500">
      Choisissez les canaux de réception pour chaque type d'événement.
    </p>
    <table class="mt-4 w-full text-sm">
      <thead>
        <tr class="border-b border-gray-200">
          <th class="py-2 text-left font-medium text-gray-700">Type</th>
          <th
            v-for="c in CHANNELS"
            :key="c.value"
            class="py-2 px-2 text-center font-medium text-gray-700"
          >
            {{ c.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="k in KINDS" :key="k.value" class="border-b border-gray-100">
          <td class="py-2 text-gray-900">{{ k.label }}</td>
          <td
            v-for="c in CHANNELS"
            :key="c.value"
            class="py-2 px-2 text-center"
          >
            <input
              type="checkbox"
              class="h-4 w-4 rounded border-gray-300 text-brand-600"
              :checked="store.isEnabled(k.value, c.value)"
              :data-testid="`pref-${k.value}-${c.value}`"
              @change="(e) => toggle(k.value, c.value, (e.target as HTMLInputElement).checked)"
            />
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="store.saving" class="mt-2 text-xs text-gray-500">Enregistrement…</p>
    <p v-else-if="store.error" class="mt-2 text-xs text-red-700">{{ store.error }}</p>
  </section>
</template>
