<script setup lang="ts">
// F42 T027 — Step 3 : CGU + RGPD
import { computed, ref } from "vue"
import { useT } from "~/composables/useT"

interface StepData {
  cgu: boolean
  rgpd: boolean
}

const props = defineProps<{ submitting?: boolean; initial?: Partial<StepData> }>()
const emit = defineEmits<{
  (e: "next", data: StepData): void
  (e: "previous"): void
}>()

const { t } = useT()

const cgu = ref(props.initial?.cgu ?? false)
const rgpd = ref(props.initial?.rgpd ?? false)

const canSubmit = computed(() => cgu.value && rgpd.value)

function onSubmit() {
  if (!canSubmit.value) return
  emit("next", { cgu: cgu.value, rgpd: rgpd.value })
}
</script>

<template>
  <form class="space-y-5" @submit.prevent="onSubmit" data-testid="step-consentements">
    <h2 class="text-lg font-semibold">{{ t("auth.register.step3.title") }}</h2>

    <label class="flex items-start gap-3 text-sm">
      <input v-model="cgu" type="checkbox" class="mt-0.5 h-4 w-4 rounded border-gray-300" />
      <span>
        {{ t("auth.register.step3.cgu") }}
        <NuxtLink to="/cgu" class="underline text-brand-700" target="_blank">
          {{ t("auth.register.step3.cgu_link") }}
        </NuxtLink>
      </span>
    </label>

    <label class="flex items-start gap-3 text-sm">
      <input v-model="rgpd" type="checkbox" class="mt-0.5 h-4 w-4 rounded border-gray-300" />
      <span>
        {{ t("auth.register.step3.rgpd") }}
        <NuxtLink to="/rgpd" class="underline text-brand-700" target="_blank">
          {{ t("auth.register.step3.rgpd_link") }}
        </NuxtLink>
      </span>
    </label>

    <div class="flex justify-between">
      <button
        type="button"
        class="text-sm text-gray-600 hover:text-gray-900 underline"
        @click="emit('previous')"
      >
        {{ t("auth.register.previous") }}
      </button>
      <button
        type="submit"
        :disabled="!canSubmit || submitting"
        class="bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-medium px-5 py-2 rounded-lg"
      >
        {{ submitting ? t("auth.register.submitting") : t("auth.register.submit") }}
      </button>
    </div>
  </form>
</template>
