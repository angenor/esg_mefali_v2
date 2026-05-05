<script setup lang="ts">
// F49 T025 — ReportDrawer : drawer slide-in droite pour aperçu PDF + métadonnées.
import { computed, ref, watch, onMounted, onBeforeUnmount } from "vue"
import { useReportsStore } from "~/stores/reports"
import { useSignedPdfUrl } from "~/composables/useSignedPdfUrl"
import { reportsApi } from "~/services/api/reports"

interface Props {
  rapportId: string | null
  open: boolean
}
const props = defineProps<Props>()
const emit = defineEmits<{ (e: "close"): void }>()

const store = useReportsStore()
const idRef = computed(() => props.rapportId)
const rapport = computed(() =>
  props.rapportId ? store.byId(props.rapportId) : null,
)
const { url, loading, error, isExpired } = useSignedPdfUrl(idRef)

function close() {
  emit("close")
}

// Animation gsap optionnelle ; on dégrade gracieusement si gsap indisponible.
const panelRef = ref<HTMLElement | null>(null)
let lastFocused: HTMLElement | null = null

watch(
  () => props.open,
  async (isOpen) => {
    if (typeof window === "undefined") return
    if (isOpen) {
      lastFocused = (document.activeElement as HTMLElement | null) ?? null
      await new Promise((r) => requestAnimationFrame(() => r(null)))
      try {
        const { gsap } = await import("gsap")
        if (panelRef.value) {
          gsap.fromTo(
            panelRef.value,
            { x: "100%" },
            { x: "0%", duration: 0.25, ease: "power2.out" },
          )
        }
      } catch {
        /* gsap absent : le drawer apparaît sans animation */
      }
      panelRef.value?.focus()
    } else if (lastFocused) {
      lastFocused.focus()
      lastFocused = null
    }
  },
)

function onKeydown(ev: KeyboardEvent) {
  if (props.open && ev.key === "Escape") close()
}
onMounted(() => {
  if (typeof window !== "undefined") {
    window.addEventListener("keydown", onKeydown)
  }
})
onBeforeUnmount(() => {
  if (typeof window !== "undefined") {
    window.removeEventListener("keydown", onKeydown)
  }
})

function downloadUrl(id: string): string {
  return reportsApi.buildDownloadUrl(id)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-50 bg-black/40"
        aria-hidden="true"
        @click="close"
      />
    </Transition>
    <Transition name="slide">
      <aside
        v-if="open && rapport"
        ref="panelRef"
        class="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col bg-white shadow-2xl outline-none focus:outline-none"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="`drawer-title-${rapport.id}`"
        tabindex="-1"
        data-testid="report-drawer"
      >
        <header
          class="flex items-center justify-between border-b border-gray-200 px-4 py-3"
        >
          <h2
            :id="`drawer-title-${rapport.id}`"
            class="text-base font-semibold text-gray-900"
          >
            {{ rapport.download_filename }}
          </h2>
          <button
            type="button"
            class="rounded p-1 text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
            aria-label="Fermer le panneau"
            @click="close"
          >
            <span aria-hidden="true">×</span>
          </button>
        </header>
        <div class="flex flex-1 overflow-hidden">
          <div class="flex-1 bg-gray-100">
            <div
              v-if="loading"
              class="flex h-full items-center justify-center text-sm text-gray-500"
            >
              Chargement de l'aperçu…
            </div>
            <div
              v-else-if="error || isExpired || !url"
              class="flex h-full flex-col items-center justify-center gap-3 p-6 text-center text-sm text-gray-600"
            >
              <p>L'aperçu inline n'est pas disponible.</p>
              <a
                :href="downloadUrl(rapport.id)"
                target="_blank"
                rel="noopener"
                class="rounded-md bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700"
              >
                Télécharger le PDF
              </a>
            </div>
            <iframe
              v-else
              :src="url"
              :title="`Aperçu de ${rapport.download_filename}`"
              class="h-full w-full border-0"
              data-testid="preview-iframe"
            />
          </div>
          <aside class="w-72 shrink-0 overflow-y-auto border-l border-gray-200 bg-white p-4 text-sm">
            <dl class="space-y-3">
              <div>
                <dt class="text-xs uppercase text-gray-500">Type</dt>
                <dd class="font-medium capitalize">{{ rapport.type }}</dd>
              </div>
              <div v-if="rapport.referentiels?.length">
                <dt class="text-xs uppercase text-gray-500">Référentiels</dt>
                <dd class="font-mono text-xs">{{ rapport.referentiels.join(", ") }}</dd>
              </div>
              <div>
                <dt class="text-xs uppercase text-gray-500">Date</dt>
                <dd>{{ new Date(rapport.created_at).toLocaleString("fr-FR") }}</dd>
              </div>
              <div>
                <dt class="text-xs uppercase text-gray-500">Taille</dt>
                <dd>
                  {{
                    rapport.size_bytes
                      ? `${Math.round(rapport.size_bytes / 1024)} Ko`
                      : "—"
                  }}
                </dd>
              </div>
              <div>
                <dt class="text-xs uppercase text-gray-500">Statut</dt>
                <dd>{{ rapport.status }}</dd>
              </div>
              <div v-if="rapport.hash_sha256">
                <dt class="text-xs uppercase text-gray-500">Hash SHA-256</dt>
                <dd class="break-all font-mono text-[10px]">{{ rapport.hash_sha256 }}</dd>
              </div>
            </dl>
          </aside>
        </div>
      </aside>
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
.slide-leave-active {
  transition: transform 0.2s ease-in;
}
.slide-leave-to {
  transform: translateX(100%);
}
</style>
