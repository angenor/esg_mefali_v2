<script setup lang="ts">
// F42 T026 — Step 2 : entreprise (raison sociale + secteur autocomplete F08)
import { computed, ref, watch } from "vue"
import { useT } from "~/composables/useT"

interface StepData {
  raison_sociale: string
  secteur: string
}

interface SecteurOption {
  id: string
  label: string
}

const props = defineProps<{ initial?: Partial<StepData> }>()
const emit = defineEmits<{
  (e: "next", data: StepData): void
  (e: "previous"): void
}>()

const { t } = useT()

const raisonSociale = ref(props.initial?.raison_sociale ?? "")
const secteurQuery = ref(props.initial?.secteur ?? "")
const selectedSecteur = ref(props.initial?.secteur ?? "")
const suggestions = ref<SecteurOption[]>([])
const showSuggestions = ref(false)
const submitted = ref(false)

const config = useRuntimeConfig()

let timer: ReturnType<typeof setTimeout> | null = null
watch(secteurQuery, (q) => {
  if (timer) clearTimeout(timer)
  if (!q || q.length < 2) {
    suggestions.value = []
    return
  }
  timer = setTimeout(async () => {
    try {
      const data = await $fetch<{ items: SecteurOption[] }>(
        `${config.public.apiBase}/catalog/secteurs`,
        { params: { q } },
      )
      suggestions.value = data.items ?? []
    } catch {
      suggestions.value = []
    }
  }, 200)
})

function pick(s: SecteurOption) {
  secteurQuery.value = s.label
  selectedSecteur.value = s.label
  showSuggestions.value = false
}

const canSubmit = computed(
  () => raisonSociale.value.trim().length >= 2 && selectedSecteur.value.length > 0,
)

function onSubmit() {
  submitted.value = true
  if (!canSubmit.value) return
  emit("next", {
    raison_sociale: raisonSociale.value.trim(),
    secteur: selectedSecteur.value,
  })
}
</script>

<template>
  <form class="space-y-5" @submit.prevent="onSubmit" data-testid="step-entreprise">
    <h2 class="text-lg font-semibold">{{ t("auth.register.step2.title") }}</h2>

    <div>
      <label for="r-rs" class="block text-sm font-medium">
        {{ t("auth.register.step2.raison_sociale") }}
      </label>
      <input
        id="r-rs"
        v-model="raisonSociale"
        type="text"
        required
        minlength="2"
        class="mt-1 w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-brand-500"
      />
    </div>

    <div class="relative">
      <label for="r-sect" class="block text-sm font-medium">
        {{ t("auth.register.step2.secteur") }}
      </label>
      <input
        id="r-sect"
        v-model="secteurQuery"
        type="text"
        :placeholder="t('auth.register.step2.secteur_placeholder')"
        autocomplete="off"
        class="mt-1 w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-brand-500"
        @focus="showSuggestions = true"
        @blur="setTimeout(() => (showSuggestions = false), 150)"
        @input="selectedSecteur = ''"
      />
      <ul
        v-if="showSuggestions && suggestions.length"
        class="absolute z-10 w-full mt-1 bg-white border rounded-lg shadow max-h-56 overflow-auto"
      >
        <li
          v-for="s in suggestions"
          :key="s.id"
          class="px-3 py-2 hover:bg-gray-50 cursor-pointer text-sm"
          @mousedown.prevent="pick(s)"
        >
          {{ s.label }}
        </li>
      </ul>
      <p
        v-if="submitted && !selectedSecteur"
        class="text-xs text-red-600 mt-1"
      >
        {{ t("auth.register.step2.secteur_required") }}
      </p>
    </div>

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
        :disabled="!canSubmit"
        class="bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-medium px-5 py-2 rounded-lg"
      >
        {{ t("auth.register.next") }}
      </button>
    </div>
  </form>
</template>
