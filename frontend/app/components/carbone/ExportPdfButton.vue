<script setup lang="ts">
// F47 T089 [US9] — Bouton "Exporter PDF" (placeholder MVP, F51 à venir).
// Cf. specs/047-empreinte-carbone-ui/contracts/frontend-components.md §ExportPdfButton.

import { ref } from "vue"
import UiButton from "~/components/ui/UiButton.vue"
import UiModal from "~/components/ui/UiModal.vue"
import { useT } from "~/composables/useT"

interface Props {
  year: number
  ready?: boolean
}

const props = withDefaults(defineProps<Props>(), { ready: false })

const { t } = useT()
const open = ref(false)

function onClick(): void {
  if (props.ready) {
    // Délégation future à useExportPdf({ section: "carbon", year }).
    return
  }
  open.value = true
}
</script>

<template>
  <div>
    <UiButton variant="secondary" size="sm" @click="onClick">
      {{ t("carbon.export.button") }}
    </UiButton>
    <UiModal v-model="open" size="sm">
      <template #header>
        <h3 class="text-lg font-semibold">
          {{ t("carbon.export.placeholderTitle") }}
        </h3>
      </template>
      <p class="text-sm text-neutral-700">
        {{ t("carbon.export.placeholderDescription") }}
      </p>
      <template #footer>
        <UiButton variant="secondary" size="sm" @click="open = false">
          {{ t("carbon.export.close") }}
        </UiButton>
      </template>
    </UiModal>
  </div>
</template>
