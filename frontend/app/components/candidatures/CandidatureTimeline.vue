<script setup lang="ts">
// F51 T068 / T096 — Timeline verticale d'événements + commentaires admin.
import type { TimelineEvent } from "~/types/candidatures"

interface Props {
  events: TimelineEvent[]
}
defineProps<Props>()

const EVENT_LABELS: Record<string, string> = {
  created: "Candidature créée",
  step_changed: "Étape modifiée",
  status_changed: "Statut modifié",
  submitted: "Candidature soumise",
  updated: "Mise à jour",
}
</script>

<template>
  <ol class="relative space-y-4 border-l-2 border-emerald-100 pl-6">
    <li v-if="events.length === 0" class="text-sm text-gray-500">
      Aucune activité enregistrée.
    </li>
    <li v-for="(ev, i) in events" :key="i" class="relative">
      <span
        class="absolute -left-[35px] top-1 flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 ring-4 ring-emerald-100"
        aria-hidden="true"
      />
      <div class="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
        <header class="flex items-center justify-between gap-3">
          <strong class="text-sm">
            {{ EVENT_LABELS[ev.event] ?? ev.event }}
          </strong>
          <time class="text-xs text-gray-500">
            {{ new Date(ev.ts).toLocaleString("fr-FR") }}
          </time>
        </header>
        <p
          v-if="ev.field"
          class="mt-1 text-xs text-gray-600"
        >
          <code class="rounded bg-gray-100 px-1.5 py-0.5">{{ ev.field }}</code>
          <template v-if="ev.from !== undefined && ev.from !== null">
            : <em>{{ ev.from }}</em> →
          </template>
          <strong v-if="ev.to !== undefined && ev.to !== null">{{ ev.to }}</strong>
        </p>
        <p v-if="ev.comment" class="mt-2 text-sm text-gray-700">
          « {{ ev.comment }} »
        </p>
        <p v-if="ev.by" class="mt-1 text-xs text-gray-500">par {{ ev.by }}</p>
      </div>
    </li>
  </ol>
</template>
