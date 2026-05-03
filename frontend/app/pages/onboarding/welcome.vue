<script setup lang="ts">
// F42 T033 — Page d'atterrissage post-register : démarrage du tour
import { useT } from "~/composables/useT"
import { useOnboardingTour } from "~/composables/useOnboardingTour"
import { useUserPreferencesStore } from "~/stores/userPreferences"
import FullscreenTourStep from "~/components/onboarding/FullscreenTourStep.vue"

definePageMeta({
  title: "Bienvenue",
})

const { t } = useT()
const router = useRouter()
const prefs = useUserPreferencesStore()
const { start } = useOnboardingTour()

const launching = ref(false)

async function startTour() {
  launching.value = true
  try {
    if (!prefs.loaded) await prefs.load().catch(() => null)
    await start()
  } finally {
    launching.value = false
    await router.push("/dashboard")
  }
}

async function skipForNow() {
  try {
    await prefs.set("skipped")
  } finally {
    await router.push("/dashboard")
  }
}
</script>

<template>
  <main class="min-h-screen flex items-center justify-center px-6 py-12">
    <div class="max-w-lg w-full bg-white rounded-2xl shadow-sm p-8 space-y-6 text-center">
      <h1 class="text-2xl font-bold">{{ t("onboarding.welcome.title") }}</h1>
      <p class="text-gray-700">{{ t("onboarding.welcome.subtitle") }}</p>
      <div class="flex flex-col sm:flex-row gap-3 justify-center pt-4">
        <button
          type="button"
          class="bg-brand-600 hover:bg-brand-700 text-white font-medium px-5 py-2.5 rounded-lg disabled:opacity-50"
          :disabled="launching"
          @click="startTour"
        >
          {{ t("onboarding.welcome.start") }}
        </button>
        <button
          type="button"
          class="text-sm text-gray-700 hover:text-gray-900 underline px-5 py-2.5"
          @click="skipForNow"
        >
          {{ t("onboarding.welcome.skip") }}
        </button>
      </div>
    </div>
    <FullscreenTourStep />
  </main>
</template>
