<script setup lang="ts">
// F43 T040 — ProjetCard : carte projet (statut, secteur, date, score badge, sous-badge candidature).
import { computed } from "vue"
import type { ProjetSummary, ProjetStatut } from "~/stores/projets"
import { useT, type LocaleKey } from "~/composables/useT"

interface Props {
  projet: ProjetSummary
}

const props = defineProps<Props>()
const { t } = useT()

const statutLabel = computed<string>(() => {
  const k = `profil.projets.status.${props.projet.statut}` as LocaleKey
  return t(k)
})

type ScoreColor = "vert" | "orange" | "rouge"
const scoreColor = computed<ScoreColor | null>(() => {
  const s = props.projet.score_esg
  if (s == null) return null
  if (s >= 75) return "vert"
  if (s >= 50) return "orange"
  return "rouge"
})

const updatedAgo = computed<string>(() => {
  const d = new Date(props.projet.updated_at)
  const diff = Date.now() - d.getTime()
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  if (days >= 1) return t("profil.projets.card.ago", { time: `${days}j` })
  if (hours >= 1) return t("profil.projets.card.ago", { time: `${hours}h` })
  if (minutes >= 1) return t("profil.projets.card.ago", { time: `${minutes}min` })
  return t("profil.projets.card.ago", { time: "<1min" })
})
</script>

<template>
  <article class="projet-card" :data-status="projet.statut">
    <header class="projet-card__header">
      <h3 class="projet-card__title">{{ projet.nom }}</h3>
      <span class="projet-card__status">{{ statutLabel }}</span>
    </header>
    <p v-if="projet.secteur" class="projet-card__secteur">{{ projet.secteur }}</p>
    <p class="projet-card__updated">{{ updatedAgo }}</p>
    <footer class="projet-card__footer">
      <span
        v-if="projet.score_esg != null"
        class="projet-card__score"
        :data-color="scoreColor || undefined"
      >
        {{ t("profil.projets.card.score", { score: projet.score_esg }) }}
      </span>
      <span v-if="projet.has_active_candidature" class="projet-card__candidature">
        {{ t("profil.projets.derived.candidature_en_cours") }}
      </span>
    </footer>
  </article>
</template>

<style scoped>
.projet-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 0.75rem;
  padding: 1rem 1.125rem;
  display: grid;
  gap: 0.5rem;
  cursor: pointer;
  transition: border-color 120ms ease, box-shadow 120ms ease;
}
.projet-card:hover {
  border-color: #15803d;
  box-shadow: 0 4px 14px -6px rgba(15, 23, 42, 0.12);
}
.projet-card__header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 0.5rem;
}
.projet-card__title {
  font-weight: 600;
  font-size: 1rem;
  color: #0f172a;
}
.projet-card__status {
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  background: #f1f5f9;
  color: #475569;
  font-weight: 500;
}
.projet-card[data-status="brouillon"] .projet-card__status {
  background: #fef9c3;
  color: #854d0e;
}
.projet-card[data-status="en_recherche_financement"] .projet-card__status {
  background: #dbeafe;
  color: #1e40af;
}
.projet-card[data-status="finance"] .projet-card__status,
.projet-card[data-status="en_execution"] .projet-card__status {
  background: #dcfce7;
  color: #166534;
}
.projet-card__secteur,
.projet-card__updated {
  color: #64748b;
  font-size: 0.8125rem;
}
.projet-card__footer {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.25rem;
}
.projet-card__score {
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-weight: 600;
}
.projet-card__score[data-color="vert"] {
  background: #dcfce7;
  color: #166534;
}
.projet-card__score[data-color="orange"] {
  background: #ffedd5;
  color: #9a3412;
}
.projet-card__score[data-color="rouge"] {
  background: #fee2e2;
  color: #991b1b;
}
.projet-card__candidature {
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  background: #ede9fe;
  color: #5b21b6;
  font-weight: 500;
}
</style>
