<script setup lang="ts">
// F44 T046 — Bouton d'export RGPD art. 20 / UEMOA 20/2010 (cf. C-COMP-7).
//
// - Désactivé pendant download + 2 s post-download (anti double-clic).
// - Toasts succès/erreur gérés par le composable.
// - Émet `exported` après download réussi (télémétrie future).
import { useDataExport } from "~/composables/useDataExport"
import { useT } from "~/composables/useT"

interface Emits {
  (e: "exported"): void
}

const emit = defineEmits<Emits>()
const { isDownloading, download } = useDataExport()
const { t } = useT()

async function onClick(): Promise<void> {
  if (isDownloading.value) return
  const before = isDownloading.value
  await download()
  // Émettre seulement après succès (best-effort : on ne distingue pas l'erreur ici,
  // mais le toast d'erreur du composable signale déjà un échec).
  if (!before) emit("exported")
}
</script>

<template>
  <button
    type="button"
    class="export-button"
    :disabled="isDownloading"
    :aria-busy="isDownloading || undefined"
    data-testid="export-button"
    @click="onClick"
  >
    {{ t("dashboard.export.button") }}
  </button>
</template>

<style scoped>
.export-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border, #ddd);
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text, #222);
  cursor: pointer;
  transition: background 0.15s ease-out;
}
.export-button:hover:not(:disabled),
.export-button:focus-visible:not(:disabled) {
  background: var(--color-surface-soft, #f5f5f5);
  outline: 2px solid var(--color-focus, #0a7d4d);
  outline-offset: 2px;
}
.export-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
