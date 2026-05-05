<script setup lang="ts">
// F47 T085 [US8] — Switch ADEME ↔ IPCC (désactivé MVP, badge "Estimation").
// Cf. specs/047-empreinte-carbone-ui/contracts/frontend-components.md §FactorReferentielSwitch.

import UiSwitch from "~/components/ui/UiSwitch.vue"
import UiBadge from "~/components/ui/UiBadge.vue"
import UiTooltip from "~/components/ui/UiTooltip.vue"
import { useT } from "~/composables/useT"

interface Props {
  modelValue?: "ademe" | "ipcc"
  disabled?: boolean
}

withDefaults(defineProps<Props>(), {
  modelValue: "ademe",
  disabled: true,
})

defineEmits<{ "update:modelValue": [value: "ademe" | "ipcc"] }>()

const { t } = useT()
</script>

<template>
  <div
    class="flex flex-wrap items-center gap-3 rounded-xl border border-neutral-200 bg-white px-4 py-3"
    :aria-disabled="disabled || undefined"
  >
    <span class="text-sm font-medium text-neutral-800">
      {{ t("carbon.factorSwitch.title") }}
    </span>
    <span class="text-sm text-neutral-700">
      {{ t("carbon.factorSwitch.ademeLabel") }}
    </span>
    <UiTooltip placement="top" :disabled="!disabled">
      <UiSwitch
        :model-value="modelValue === 'ipcc'"
        :disabled="disabled"
        :aria-label="t('carbon.factorSwitch.title')"
        @update:model-value="(v) => $emit('update:modelValue', v ? 'ipcc' : 'ademe')"
      />
      <template #content>
        <span>{{ t("carbon.factorSwitch.disabledTooltip") }}</span>
      </template>
    </UiTooltip>
    <span class="text-sm text-neutral-700">
      {{ t("carbon.factorSwitch.ipccLabel") }}
    </span>
    <UiBadge severity="warning" variant="subtle">
      {{ t("carbon.factorSwitch.estimateBadge") }}
    </UiBadge>
  </div>
</template>
