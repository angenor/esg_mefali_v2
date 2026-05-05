<script setup lang="ts">
// F52 US6 — Mini-chat IA contextuel (placeholder MVP).
// La saisie utilisateur est déléguée à un mini bottom-sheet (P10) ; ici on
// rend les bulles read-only renvoyées par le backend.
import { ref } from "vue"

interface Bubble {
  id: string
  role: "user" | "assistant"
  text: string
}

const bubbles = ref<Bubble[]>([
  {
    id: "welcome",
    role: "assistant",
    text:
      "Bienvenue. Tapez sur \"Répondre librement\" pour interagir, ou consultez vos candidatures.",
  },
])

const sheetOpen = ref(false)
const draft = ref("")

function open(): void {
  sheetOpen.value = true
}
function close(): void {
  sheetOpen.value = false
  draft.value = ""
}
function submit(): void {
  const text = draft.value.trim()
  if (!text) return
  bubbles.value = [
    ...bubbles.value,
    { id: `u-${Date.now()}`, role: "user", text },
    {
      id: `a-${Date.now() + 1}`,
      role: "assistant",
      text: "Réponse contextuelle disponible une fois connecté à l'app web.",
    },
  ]
  close()
}
</script>

<template>
  <section class="space-y-2 px-3 py-2" data-testid="mini-chat-view">
    <ul class="space-y-2">
      <li
        v-for="b in bubbles"
        :key="b.id"
        class="rounded border border-slate-200 bg-white p-2 text-xs"
        :class="b.role === 'user' ? 'bg-emerald-50' : ''"
        :data-testid="`chat-bubble-${b.role}`"
      >
        {{ b.text }}
      </li>
    </ul>
    <button
      type="button"
      class="w-full rounded border border-slate-300 bg-white py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
      data-testid="chat-open-sheet"
      @click="open"
    >
      Répondre librement
    </button>

    <Teleport to="body">
      <Transition name="sheet">
        <section
          v-if="sheetOpen"
          role="dialog"
          aria-label="Saisir un message"
          class="fixed inset-x-0 bottom-0 z-50 mx-auto w-full max-w-md rounded-t-xl bg-white p-4 shadow-2xl"
          data-testid="chat-sheet"
        >
          <header class="mb-2 flex items-start justify-between">
            <h2 class="text-sm font-semibold text-slate-900">Votre message</h2>
            <button class="text-slate-400" aria-label="Fermer" @click="close">×</button>
          </header>
          <textarea
            v-model="draft"
            rows="3"
            class="block w-full rounded border border-slate-300 p-2 text-xs"
            data-testid="chat-input"
            placeholder="Posez votre question…"
          ></textarea>
          <div class="mt-2 flex justify-end gap-2">
            <button
              type="button"
              class="rounded border border-slate-200 px-3 py-1 text-xs"
              @click="close"
            >
              Annuler
            </button>
            <button
              type="button"
              class="rounded bg-emerald-600 px-3 py-1 text-xs font-medium text-white"
              data-testid="chat-submit"
              @click="submit"
            >
              Envoyer
            </button>
          </div>
        </section>
      </Transition>
    </Teleport>
  </section>
</template>

<style scoped>
.sheet-enter-active,
.sheet-leave-active {
  transition: transform 220ms ease;
}
.sheet-enter-from,
.sheet-leave-to {
  transform: translateY(100%);
}
</style>
