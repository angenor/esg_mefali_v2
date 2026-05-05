<script setup lang="ts">
// F49 T045 — Footer sobre pour /verify/[id].
//
// IMPORTANT (P7) : aucun lien retour vers l'app PME (login, dashboard, etc.).
import { useVerifyI18n } from "~/composables/useVerifyI18n"

interface Props {
  lang?: "fr" | "en"
}
const props = defineProps<Props>()
const { t } = useVerifyI18n(props.lang)
</script>

<template>
  <footer
    class="border-t border-gray-200 bg-gray-50 px-4 py-6 text-sm text-gray-600"
    data-testid="verify-footer"
  >
    <nav aria-label="Liens légaux" class="mx-auto flex max-w-3xl flex-wrap gap-4">
      <a href="/mentions-legales" class="hover:underline">
        {{ t("footer.legal") }}
      </a>
      <a href="/confidentialite" class="hover:underline">
        {{ t("footer.rgpd") }}
      </a>
      <a href="/about" class="hover:underline">
        {{ t("footer.about") }}
      </a>
    </nav>
  </footer>
</template>
