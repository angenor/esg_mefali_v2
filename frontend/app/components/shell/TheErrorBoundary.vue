<script setup lang="ts">
// F38 T061 — TheErrorBoundary
interface Props {
  error: Error | null
}
const props = defineProps<Props>()
const emit = defineEmits<{ reload: [] }>()

const isDev = import.meta.dev
</script>

<template>
  <div role="alert" class="p-6" data-testid="error-boundary">
    <h2 class="text-xl font-bold text-gray-900">Une erreur est survenue</h2>
    <p class="mt-2 text-gray-600">
      Nous n'avons pas pu charger cette page. Vous pouvez réessayer.
    </p>
    <button
      type="button"
      class="mt-4 rounded bg-brand-600 px-4 py-2 text-white hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
      data-testid="error-boundary-reload"
      @click="emit('reload')"
    >
      Recharger
    </button>
    <pre
      v-if="isDev && props.error"
      class="mt-4 overflow-x-auto rounded bg-gray-50 p-3 text-xs text-red-700"
    >{{ props.error.message }}{{ props.error.stack ? '\n' + props.error.stack : '' }}</pre>
  </div>
</template>
