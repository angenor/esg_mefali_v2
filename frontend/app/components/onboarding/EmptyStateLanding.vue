<script setup lang="ts">
// F42 T062 — Empty state affiché quand profil entreprise < 50 %
import { useT } from "~/composables/useT"
import EmptyStateCard from "~/components/onboarding/EmptyStateCard.vue"

const { t } = useT()
const router = useRouter()

function goToProfile() {
  router.push("/profil")
}
</script>

<template>
  <section class="mx-auto max-w-4xl p-6" data-testid="empty-state-landing">
    <header class="text-center">
      <h1 class="text-3xl font-bold text-slate-900">{{ t("empty.title") }}</h1>
      <p class="mt-3 text-base text-slate-600">{{ t("empty.subtitle") }}</p>
      <button
        type="button"
        class="mt-6 inline-flex items-center justify-center rounded-xl bg-emerald-600 px-6 py-3 text-base font-semibold text-white shadow-sm transition hover:bg-emerald-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
        data-testid="empty-state-cta"
        @click="goToProfile"
      >
        {{ t("empty.cta") }}
      </button>
    </header>

    <div class="mt-10 grid grid-cols-1 gap-4 md:grid-cols-3">
      <EmptyStateCard
        icon="📊"
        :title="t('empty.card1.title')"
        :description="t('empty.card1.body')"
      />
      <EmptyStateCard
        icon="💶"
        :title="t('empty.card2.title')"
        :description="t('empty.card2.body')"
      />
      <EmptyStateCard
        icon="📝"
        :title="t('empty.card3.title')"
        :description="t('empty.card3.body')"
      />
    </div>
  </section>
</template>
