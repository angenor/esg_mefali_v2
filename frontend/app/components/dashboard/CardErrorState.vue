<script setup lang="ts">
// F44 T014 — État erreur générique pour cartes dashboard (cf. C-COMP-5).
import UiButton from "~/components/ui/UiButton.vue"
import { useT } from "~/composables/useT"

interface Props {
  message?: string
}

const props = withDefaults(defineProps<Props>(), {
  message: undefined,
})

const emit = defineEmits<{
  (e: "retry"): void
}>()

const { t } = useT()
</script>

<template>
  <div class="card-error" role="alert">
    <p class="card-error__message">
      {{ props.message ?? t("dashboard.card.error.message") }}
    </p>
    <UiButton variant="secondary" size="sm" @click="emit('retry')">
      {{ t("dashboard.card.error.retry") }}
    </UiButton>
  </div>
</template>

<style scoped>
.card-error {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem 0;
}
.card-error__message {
  color: var(--color-danger, #b00020);
  font-size: 0.875rem;
  margin: 0;
}
</style>
