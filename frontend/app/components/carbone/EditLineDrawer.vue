<script setup lang="ts">
// F47 T054 [US3] — Orchestrateur d'édition de ligne (sans UI propre).
//
// Monté une fois à la racine de /carbone. Écoute les demandes d'édition
// (event window 'carbon:edit-line') et délègue à `useCarbonEdit`.
// Le rendu UI est assuré par <ChatBottomSheet> (F39) via tool=ask_form.

import { onBeforeUnmount, onMounted } from "vue"
import { useCarbonEdit, type OpenDrawerArgs, type SubmitArgs } from "~/composables/useCarbonEdit"

const edit = useCarbonEdit()

const OPEN_EVENT = "carbon:edit-line:open"
const SUBMIT_EVENT = "carbon:edit-line:submit"

function onOpen(e: Event): void {
  const detail = (e as CustomEvent<OpenDrawerArgs>).detail
  if (!detail) return
  void edit.openDrawer(detail)
}

function onSubmit(e: Event): void {
  const detail = (e as CustomEvent<SubmitArgs>).detail
  if (!detail) return
  void edit.submit(detail)
}

onMounted(() => {
  if (typeof window === "undefined") return
  window.addEventListener(OPEN_EVENT, onOpen as EventListener)
  window.addEventListener(SUBMIT_EVENT, onSubmit as EventListener)
})

onBeforeUnmount(() => {
  if (typeof window === "undefined") return
  window.removeEventListener(OPEN_EVENT, onOpen as EventListener)
  window.removeEventListener(SUBMIT_EVENT, onSubmit as EventListener)
})

defineExpose({ edit })
</script>

<template>
  <span class="sr-only" aria-hidden="true" data-testid="carbon-edit-drawer-mount" />
</template>
