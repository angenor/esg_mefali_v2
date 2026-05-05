<script setup lang="ts">
// F49 T052 — Bascule FR/EN pour /verify/[id].
//
// La langue initiale est lue côté serveur via le cookie `mefali_verify_lang`,
// donc le rendu SSR ne flashe pas. Le switch ré-emet `update:lang` pour la page.
import { computed } from "vue"
import type { VerifyLang } from "~/composables/useVerifyI18n"
import { useVerifyI18n } from "~/composables/useVerifyI18n"

interface Props {
  lang: VerifyLang
}
const props = defineProps<Props>()
const emit = defineEmits<{ (e: "update:lang", v: VerifyLang): void }>()

const { setLang } = useVerifyI18n(props.lang)

function pick(next: VerifyLang) {
  if (next === props.lang) return
  setLang(next)
  emit("update:lang", next)
}

const isFr = computed(() => props.lang === "fr")
const isEn = computed(() => props.lang === "en")
</script>

<template>
  <div
    class="inline-flex overflow-hidden rounded-md border border-gray-300 text-xs font-medium"
    role="group"
    aria-label="Sélecteur de langue"
    data-testid="lang-switch"
  >
    <button
      type="button"
      class="px-3 py-1.5"
      :class="isFr ? 'bg-brand-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'"
      :aria-pressed="isFr"
      aria-label="Français"
      data-testid="lang-fr"
      @click="pick('fr')"
    >
      FR
    </button>
    <button
      type="button"
      class="border-l border-gray-300 px-3 py-1.5"
      :class="isEn ? 'bg-brand-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'"
      :aria-pressed="isEn"
      aria-label="English"
      data-testid="lang-en"
      @click="pick('en')"
    >
      EN
    </button>
  </div>
</template>
