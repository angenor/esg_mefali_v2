<script setup lang="ts">
// F42 T075 — Page d'accueil publique de confiance
// Si user authentifié → redirection /dashboard ; sinon pitch + bénéfices + témoignage.
import { onMounted } from "vue"
import { useT } from "~/composables/useT"
import { useAuthStore } from "~/stores/auth"
import PublicHero from "~/components/home/PublicHero.vue"
import PublicBenefitsGrid from "~/components/home/PublicBenefitsGrid.vue"
import PublicTestimonial from "~/components/home/PublicTestimonial.vue"

definePageMeta({
  layout: "public",
  public: true,
  title: "Accueil",
})

const { t } = useT()
const authStore = useAuthStore()
const router = useRouter()

onMounted(() => {
  if (authStore.isAuthenticated) {
    router.replace("/dashboard")
  }
})
</script>

<template>
  <main>
    <PublicHero />
    <PublicBenefitsGrid />
    <PublicTestimonial />
    <footer class="bg-white py-6 text-center text-xs text-slate-500">
      {{ t("public.footer.copyright") }}
    </footer>
  </main>
</template>
