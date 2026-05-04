<script setup lang="ts">
// F47 T043 [US2] — Popover détail facteur d'émission (version + valid_from + source).
// Cf. specs/047-empreinte-carbone-ui/contracts/frontend-components.md §FactorSourcePopover.

import { ref } from "vue"
import VizSourcePin from "~/components/viz/VizSourcePin.vue"
import UiPopover from "~/components/ui/UiPopover.vue"
import { useT } from "~/composables/useT"

interface Props {
  factorId: string
  factorVersion: number
  factorSourceId: string
  validFrom?: string
}

const props = defineProps<Props>()

const { t } = useT()

const open = ref(false)
</script>

<template>
  <UiPopover v-model="open">
    <template #trigger>
      <button
        type="button"
        class="text-xs underline text-neutral-600 hover:text-neutral-900"
        :aria-haspopup="true"
        :aria-expanded="open"
      >
        v{{ factorVersion }}
      </button>
    </template>
    <template #content>
      <div class="p-3 max-w-xs">
        <p class="text-xs font-medium text-neutral-700 mb-2">
          {{
            t("carbon.factor.version", {
              version: factorVersion,
              validFrom: validFrom ?? "—",
            })
          }}
        </p>
        <VizSourcePin :source_id="factorSourceId" />
      </div>
    </template>
  </UiPopover>
</template>
