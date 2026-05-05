<script setup lang="ts">
// F49 T037 — Modale de révocation d'une attestation avec motif catégorisé.
import { ref, watch } from "vue"
import { useAttestationsStore } from "~/stores/attestations"
import { useToast } from "~/composables/useToast"
import {
  REVOKE_REASONS,
  type Attestation,
  type RevokeReason,
} from "~/types/attestations"

interface Props {
  open: boolean
  attestation: Attestation | null
}
const props = defineProps<Props>()
const emit = defineEmits<{ (e: "close"): void; (e: "revoked"): void }>()

const store = useAttestationsStore()
const toast = useToast()

const REASON_LABELS: Record<RevokeReason, string> = {
  erreur_emission: "Erreur d'émission",
  donnees_invalidees: "Données invalidées",
  demande_pme: "Demande de la PME",
  expiration_anticipee: "Expiration anticipée",
  autre: "Autre motif",
}

const reason = ref<RevokeReason | "">("")
const submitting = ref(false)
const errorMessage = ref<string | null>(null)

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      reason.value = ""
      submitting.value = false
      errorMessage.value = null
    }
  },
  { immediate: true },
)

async function submit() {
  if (!reason.value || !props.attestation || submitting.value) return
  submitting.value = true
  errorMessage.value = null
  try {
    await store.revoke(props.attestation.id, reason.value)
    toast.push({
      severity: "success",
      message: "Attestation révoquée.",
      duration: 4000,
    })
    emit("revoked")
    emit("close")
  } catch (err: unknown) {
    errorMessage.value =
      err instanceof Error
        ? err.message
        : "La révocation a échoué. Réessayez."
  } finally {
    submitting.value = false
  }
}

function close() {
  if (submitting.value) return
  emit("close")
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open && attestation"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="revoke-modal-title"
        data-testid="revoke-modal"
        @click.self="close"
      >
        <div class="w-full max-w-md rounded-lg bg-white shadow-xl" @click.stop>
          <header
            class="flex items-center justify-between border-b border-gray-200 px-4 py-3"
          >
            <h2 id="revoke-modal-title" class="text-base font-semibold text-red-700">
              Révoquer l'attestation
            </h2>
            <button
              type="button"
              class="rounded p-1 text-gray-500 hover:bg-gray-100"
              aria-label="Fermer"
              :disabled="submitting"
              @click="close"
            >
              <span aria-hidden="true">×</span>
            </button>
          </header>

          <form class="space-y-4 p-4 text-sm" @submit.prevent="submit">
            <p class="text-gray-700">
              Cette action est irréversible. La page publique
              <span class="font-mono text-xs">/verify/{{ attestation.public_id.slice(0, 12) }}…</span>
              affichera un bandeau « révoquée » sous 60 s.
            </p>

            <fieldset class="space-y-2">
              <legend class="block text-xs font-medium uppercase text-gray-500">
                Motif (obligatoire)
              </legend>
              <div
                v-for="r in REVOKE_REASONS"
                :key="r"
                class="flex items-center gap-2"
              >
                <input
                  :id="`revoke-reason-${r}`"
                  v-model="reason"
                  type="radio"
                  :value="r"
                  name="revoke-reason"
                  class="h-4 w-4 border-gray-300 text-red-600 focus:ring-red-500"
                  :data-testid="`reason-${r}`"
                  required
                />
                <label
                  :for="`revoke-reason-${r}`"
                  class="text-gray-800"
                >
                  {{ REASON_LABELS[r] }}
                </label>
              </div>
            </fieldset>

            <p
              v-if="errorMessage"
              class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-red-700"
              role="alert"
              data-testid="revoke-error"
            >
              {{ errorMessage }}
            </p>

            <footer class="flex justify-end gap-2 pt-2">
              <button
                type="button"
                class="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                :disabled="submitting"
                @click="close"
              >
                Annuler
              </button>
              <button
                type="submit"
                class="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="!reason || submitting"
                data-testid="confirm-revoke"
              >
                {{ submitting ? "Révocation…" : "Confirmer la révocation" }}
              </button>
            </footer>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
