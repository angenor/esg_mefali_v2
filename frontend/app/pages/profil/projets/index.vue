<script setup lang="ts">
// F43 T047 — /profil/projets : liste cards + empty state + bouton « Nouveau projet ».
import { computed, ref } from "vue"
import { storeToRefs } from "pinia"
import { useProjetsStore, type ProjetRead } from "~/stores/projets"
import { useT } from "~/composables/useT"
import ProjetCard from "~/components/profil/ProjetCard.vue"
import ProjetEmptyState from "~/components/profil/ProjetEmptyState.vue"
import ProjetWizard from "~/components/profil/ProjetWizard.vue"

definePageMeta({
  layout: "default",
  middleware: ["pme-only"],
  breadcrumb: [{ label: "Projets" }],
  title: "Projets",
})

const { t } = useT()
const store = useProjetsStore()
const router = useRouter()

await useAsyncData("projets-list", () => store.loadList())

const { list, loading } = storeToRefs(store)
const active = computed(() => list.value.filter((p) => !p.deleted_at))

const wizardOpen = ref(false)

function openWizard(): void {
  wizardOpen.value = true
}

function closeWizard(): void {
  wizardOpen.value = false
}

function onCreated(projet: ProjetRead): void {
  wizardOpen.value = false
  void router.push(`/profil/projets/${projet.id}`)
}

function goToProjet(id: string): void {
  void router.push(`/profil/projets/${id}`)
}
</script>

<template>
  <section class="projets-page" aria-labelledby="projets-page-title">
    <header class="projets-page__header">
      <h1 id="projets-page-title">{{ t("profil.projets.title") }}</h1>
      <button
        v-if="active.length > 0"
        type="button"
        class="projets-page__cta"
        @click="openWizard"
      >
        {{ t("profil.projets.cta.new") }}
      </button>
    </header>

    <p v-if="loading && active.length === 0" aria-live="polite">Chargement…</p>

    <ProjetEmptyState v-else-if="active.length === 0" @create="openWizard" />

    <div v-else class="projets-page__grid">
      <button
        v-for="p in active"
        :key="p.id"
        type="button"
        class="projets-page__card-btn"
        :aria-label="`Ouvrir ${p.nom}`"
        @click="goToProjet(p.id)"
      >
        <ProjetCard :projet="p" />
      </button>
    </div>

    <ProjetWizard :open="wizardOpen" @close="closeWizard" @created="onCreated" />
  </section>
</template>

<style scoped>
.projets-page {
  display: grid;
  gap: 1rem;
  padding: 1rem;
  max-width: 1200px;
  margin: 0 auto;
}
.projets-page__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}
.projets-page__header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #0f172a;
}
.projets-page__cta {
  background: #15803d;
  color: #fff;
  border: 0;
  border-radius: 0.5rem;
  padding: 0.55rem 1rem;
  font-weight: 600;
  cursor: pointer;
}
.projets-page__cta:focus-visible {
  outline: 2px solid #166534;
  outline-offset: 2px;
}
.projets-page__grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
}
.projets-page__card-btn {
  background: none;
  border: 0;
  padding: 0;
  text-align: left;
  cursor: pointer;
}
.projets-page__card-btn:focus-visible {
  outline: 2px solid #15803d;
  outline-offset: 2px;
  border-radius: 0.75rem;
}
</style>
