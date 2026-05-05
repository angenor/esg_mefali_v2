<script setup lang="ts">
// F42 T031 — Modal fullscreen pour fallback mobile du tour
import { onBeforeUnmount, onMounted, ref } from "vue"
import { registerFullscreenAdapter } from "~/composables/useOnboardingTour"
import { useT } from "~/composables/useT"

interface FallbackStep {
  title: string
  body: string
  selector: string
}

const { t } = useT()

const visible = ref(false)
const steps = ref<FallbackStep[]>([])
const index = ref(0)
const handlers = ref<{
  onSkip: () => void
  onDismiss: () => void
  onComplete: () => void
} | null>(null)

function show(s: FallbackStep[], h: {
  onSkip: () => void
  onDismiss: () => void
  onComplete: () => void
}) {
  steps.value = s
  index.value = 0
  handlers.value = h
  visible.value = true
}

function close() {
  visible.value = false
  steps.value = []
  handlers.value = null
}

function next() {
  if (index.value < steps.value.length - 1) {
    index.value++
  } else {
    handlers.value?.onComplete()
    close()
  }
}

function skip() {
  handlers.value?.onSkip()
  close()
}

function dismiss() {
  handlers.value?.onDismiss()
  close()
}

onMounted(() => {
  registerFullscreenAdapter({ show, close })
})
onBeforeUnmount(() => {
  visible.value = false
})
</script>

<template>
  <Teleport v-if="visible" to="body">
    <div
      class="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-6"
      role="dialog"
      aria-modal="true"
    >
      <div class="bg-white rounded-2xl max-w-sm w-full p-6 space-y-4">
        <h2 class="text-lg font-semibold">{{ steps[index]?.title }}</h2>
        <p class="text-sm text-gray-700">{{ steps[index]?.body }}</p>
        <div class="text-xs text-gray-500">
          {{ index + 1 }} / {{ steps.length }}
        </div>
        <div class="flex justify-between gap-2 pt-2">
          <button
            type="button"
            class="text-xs text-gray-600 underline"
            @click="dismiss"
          >
            {{ t("onboarding.tour.dismiss") }}
          </button>
          <div class="flex gap-2">
            <button
              type="button"
              class="text-sm text-gray-700 px-3 py-1.5 rounded border"
              @click="skip"
            >
              {{ t("onboarding.tour.skip") }}
            </button>
            <button
              type="button"
              class="text-sm bg-brand-600 hover:bg-brand-700 text-white px-3 py-1.5 rounded"
              @click="next"
            >
              {{ index === steps.length - 1 ? t("onboarding.tour.finish") : t("onboarding.tour.next") }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
