<script setup lang="ts">
// F49 T036 — Modale de partage d'une attestation : URL publique copiable + QR PNG.
import { computed, ref, watch } from "vue"
import { useAttestationsStore } from "~/stores/attestations"
import { useToast } from "~/composables/useToast"
import type { Attestation } from "~/types/attestations"

interface Props {
  open: boolean
  attestation: Attestation | null
}
const props = defineProps<Props>()
const emit = defineEmits<{ (e: "close"): void }>()

const store = useAttestationsStore()
const toast = useToast()

const qrDataUrl = ref<string | null>(null)
const qrBlobUrl = ref<string | null>(null)
const generating = ref(false)
const errorMessage = ref<string | null>(null)

const verifyUrl = computed(() =>
  props.attestation ? store.buildVerifyUrl(props.attestation.public_id) : "",
)

watch(
  () => [props.open, props.attestation?.public_id] as const,
  async ([isOpen, pubId]) => {
    revokeBlob()
    qrDataUrl.value = null
    errorMessage.value = null
    if (!isOpen || !pubId) return
    generating.value = true
    try {
      const qrcode = await import("qrcode")
      qrDataUrl.value = await qrcode.toDataURL(verifyUrl.value, {
        errorCorrectionLevel: "H",
        width: 256,
        margin: 2,
      })
      const blob = await store.buildQrPng(pubId)
      qrBlobUrl.value = URL.createObjectURL(blob)
    } catch (err: unknown) {
      errorMessage.value =
        err instanceof Error ? err.message : "Échec de la génération du QR."
    } finally {
      generating.value = false
    }
  },
  { immediate: true },
)

function revokeBlob() {
  if (qrBlobUrl.value) {
    URL.revokeObjectURL(qrBlobUrl.value)
    qrBlobUrl.value = null
  }
}

async function copyUrl() {
  if (!verifyUrl.value) return
  try {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      await navigator.clipboard.writeText(verifyUrl.value)
    } else {
      throw new Error("Clipboard API indisponible")
    }
    toast.push({
      severity: "success",
      message: "Lien copié dans le presse-papiers.",
      duration: 3000,
    })
  } catch (err: unknown) {
    toast.push({
      severity: "error",
      message:
        err instanceof Error
          ? `Copie impossible : ${err.message}`
          : "Copie impossible.",
    })
  }
}

function close() {
  revokeBlob()
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
        aria-labelledby="share-modal-title"
        data-testid="share-modal"
        @click.self="close"
      >
        <div class="w-full max-w-md rounded-lg bg-white shadow-xl" @click.stop>
          <header
            class="flex items-center justify-between border-b border-gray-200 px-4 py-3"
          >
            <h2 id="share-modal-title" class="text-base font-semibold">
              Partager l'attestation
            </h2>
            <button
              type="button"
              class="rounded p-1 text-gray-500 hover:bg-gray-100"
              aria-label="Fermer"
              @click="close"
            >
              <span aria-hidden="true">×</span>
            </button>
          </header>

          <div class="space-y-4 p-4 text-sm">
            <div>
              <label
                for="share-url-input"
                class="mb-1 block text-xs font-medium uppercase text-gray-500"
              >
                URL publique
              </label>
              <div class="flex gap-2">
                <input
                  id="share-url-input"
                  type="text"
                  readonly
                  :value="verifyUrl"
                  class="w-full rounded-md border border-gray-300 bg-gray-50 px-3 py-2 font-mono text-xs"
                  data-testid="share-url"
                  @focus="($event.target as HTMLInputElement).select()"
                />
                <button
                  type="button"
                  class="shrink-0 rounded-md bg-brand-600 px-3 py-2 text-xs font-medium text-white hover:bg-brand-700"
                  data-testid="copy-btn"
                  @click="copyUrl"
                >
                  Copier
                </button>
              </div>
            </div>

            <div>
              <p class="mb-2 text-xs font-medium uppercase text-gray-500">
                QR Code
              </p>
              <div
                class="flex flex-col items-center gap-3 rounded-md border border-gray-200 bg-gray-50 p-4"
              >
                <div
                  v-if="generating"
                  class="text-xs text-gray-500"
                  data-testid="qr-loading"
                >
                  Génération du QR…
                </div>
                <img
                  v-else-if="qrDataUrl"
                  :src="qrDataUrl"
                  alt="QR Code de vérification"
                  width="256"
                  height="256"
                  class="h-64 w-64"
                  data-testid="qr-image"
                />
                <p
                  v-if="errorMessage"
                  class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-red-700"
                  role="alert"
                >
                  {{ errorMessage }}
                </p>
                <a
                  v-if="qrBlobUrl"
                  :href="qrBlobUrl"
                  download="attestation-qr.png"
                  class="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                  data-testid="qr-download"
                >
                  Télécharger QR PNG
                </a>
              </div>
            </div>
          </div>

          <footer
            class="flex justify-end gap-2 border-t border-gray-200 px-4 py-3"
          >
            <button
              type="button"
              class="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              @click="close"
            >
              Fermer
            </button>
          </footer>
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
