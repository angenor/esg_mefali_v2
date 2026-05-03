<script setup lang="ts">
// F42 T032 — Bouton "Relancer le tour" pour le menu Aide
import { useOnboardingTour } from "~/composables/useOnboardingTour"
import { useT } from "~/composables/useT"

const { t } = useT()
const { start } = useOnboardingTour()
</script>

<template>
  <button
    type="button"
    class="text-sm text-gray-700 hover:text-brand-700 underline"
    @click="start"
  >
    {{ t("onboarding.tour.restart") }}
  </button>
</template>
