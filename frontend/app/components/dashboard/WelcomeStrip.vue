<script setup lang="ts">
// F44 T025 — Bandeau d'accueil PME (cf. C-COMP-1).
import { computed } from "vue"
import { useT } from "~/composables/useT"

interface Props {
  raisonSociale: string
  lastDiagnosticAt: Date | null
}

const props = defineProps<Props>()
const { t } = useT()

const greeting = computed(() => {
  const h = new Date().getHours()
  const isMorning = h < 18 && h >= 4
  const key = isMorning ? "dashboard.welcome.greeting_morning" : "dashboard.welcome.greeting_evening"
  return t(key, { nom: props.raisonSociale })
})

const lastDiagnosticLabel = computed(() => {
  if (!props.lastDiagnosticAt) return t("dashboard.welcome.no_diagnostic")
  const days = Math.round(
    (Date.now() - props.lastDiagnosticAt.getTime()) / (1000 * 60 * 60 * 24),
  )
  const fmt = new Intl.RelativeTimeFormat("fr", { numeric: "auto" })
  const relative = fmt.format(-days, "day")
  return t("dashboard.welcome.last_diagnostic_relative", { relative })
})
</script>

<template>
  <header class="welcome-strip">
    <div class="welcome-strip__text">
      <h1 class="welcome-strip__title">{{ greeting }}</h1>
      <p class="welcome-strip__subtitle">{{ lastDiagnosticLabel }}</p>
    </div>
    <NuxtLink to="/chat" class="welcome-strip__cta">
      {{ t("dashboard.welcome.cta_chat") }}
    </NuxtLink>
  </header>
</template>

<style scoped>
.welcome-strip {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem 1rem;
  background: linear-gradient(135deg, rgba(10, 125, 77, 0.06), transparent);
  border-radius: 0.75rem;
  margin-bottom: 1rem;
}
@media (min-width: 768px) {
  .welcome-strip {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
}
.welcome-strip__title {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0;
  color: var(--color-text, #111);
}
.welcome-strip__subtitle {
  font-size: 0.95rem;
  color: var(--color-text-muted, #555);
  margin: 0.25rem 0 0;
}
.welcome-strip__cta {
  display: inline-block;
  padding: 0.625rem 1.25rem;
  background: var(--color-primary, #0a7d4d);
  color: white;
  border-radius: 0.5rem;
  text-decoration: none;
  font-weight: 600;
  white-space: nowrap;
}
.welcome-strip__cta:hover,
.welcome-strip__cta:focus-visible {
  background: var(--color-primary-dark, #0a6840);
  outline: 2px solid var(--color-focus, #0a7d4d);
  outline-offset: 2px;
}
</style>
