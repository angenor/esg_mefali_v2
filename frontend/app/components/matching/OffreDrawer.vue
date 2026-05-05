<script setup lang="ts">
// F51 T034 — Drawer détail offre.

import { computed, watch } from "vue"
import { useMatchingStore } from "~/stores/matching"
import { formatMoney } from "~/utils/money"

const props = defineProps<{
  open: boolean
  projetId: string | null
}>()

const emit = defineEmits<{
  close: []
}>()

const store = useMatchingStore()

watch(
  () => props.open,
  (open) => {
    if (!open) store.closeDrawer()
  },
)

const offre = computed(() => store.drawerOffre)
const loading = computed(() => store.drawerLoading)

const montantLabel = computed(() => {
  if (!offre.value) return ""
  const min = offre.value.montant_min
  const max = offre.value.montant_max
  if (min && max) return `${formatMoney(min)} – ${formatMoney(max)}`
  if (max) return `Jusqu'à ${formatMoney(max)}`
  if (min) return `À partir de ${formatMoney(min)}`
  return "Non spécifié"
})

const candidatureUrl = computed(() => {
  if (!offre.value) return "#"
  const params = new URLSearchParams()
  params.set("offre_id", offre.value.offre_id)
  if (props.projetId) params.set("projet_id", props.projetId)
  return `/candidatures/new?${params.toString()}`
})
</script>

<template>
  <Teleport to="body">
    <transition name="drawer">
      <aside
        v-if="open"
        class="offre-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="offre-drawer-title"
        @keydown.esc="emit('close')"
      >
        <div class="offre-drawer__overlay" @click="emit('close')" />
        <div class="offre-drawer__panel">
          <header class="offre-drawer__head">
            <h2 id="offre-drawer-title">{{ offre?.nom ?? "Chargement…" }}</h2>
            <button type="button" class="offre-drawer__close" aria-label="Fermer" @click="emit('close')">
              ×
            </button>
          </header>

          <div v-if="loading" class="offre-drawer__loading">Chargement…</div>

          <div v-else-if="offre" class="offre-drawer__body">
            <p class="offre-drawer__intermediaire">
              {{ offre.intermediaire.nom }}
            </p>

            <dl class="offre-drawer__meta">
              <div>
                <dt>Type</dt>
                <dd>{{ offre.type }}</dd>
              </div>
              <div>
                <dt>Montant</dt>
                <dd>{{ montantLabel }}</dd>
              </div>
              <div v-if="offre.duree_min_mois || offre.duree_max_mois">
                <dt>Durée</dt>
                <dd>
                  {{ offre.duree_min_mois ?? "?" }} – {{ offre.duree_max_mois ?? "?" }} mois
                </dd>
              </div>
            </dl>

            <section v-if="offre.description">
              <h3>Description</h3>
              <p>{{ offre.description }}</p>
            </section>

            <section v-if="offre.documents_requis.length">
              <h3>Documents requis</h3>
              <ul>
                <li v-for="d in offre.documents_requis" :key="d.key">
                  {{ d.label }} <span class="offre-drawer__format">({{ d.format }})</span>
                </li>
              </ul>
            </section>

            <section v-if="offre.conditions.length">
              <h3>Conditions</h3>
              <ul>
                <li v-for="(c, idx) in offre.conditions" :key="idx">{{ c }}</li>
              </ul>
            </section>

            <a
              v-if="offre.lien_externe"
              :href="offre.lien_externe"
              target="_blank"
              rel="noopener"
              class="offre-drawer__external"
            >
              Site externe ↗
            </a>
          </div>

          <footer v-if="offre" class="offre-drawer__footer">
            <NuxtLink :to="candidatureUrl" class="btn-primary">
              Préparer ma candidature
            </NuxtLink>
          </footer>
        </div>
      </aside>
    </transition>
  </Teleport>
</template>

<style scoped>
.offre-drawer {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  justify-content: flex-end;
}
.offre-drawer__overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
}
.offre-drawer__panel {
  position: relative;
  width: min(520px, 100%);
  height: 100%;
  background: white;
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 16px rgba(0, 0, 0, 0.15);
}
.offre-drawer__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--color-border, #e5e7eb);
}
.offre-drawer__head h2 {
  margin: 0;
  font-size: 1.1rem;
}
.offre-drawer__close {
  font-size: 1.5rem;
  background: transparent;
  border: 0;
  cursor: pointer;
  width: 2rem;
  height: 2rem;
}
.offre-drawer__loading {
  padding: 2rem;
  text-align: center;
  color: var(--color-muted, #6b7280);
}
.offre-drawer__body {
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
.offre-drawer__intermediaire {
  font-weight: 500;
  color: var(--color-muted, #4b5563);
  margin: 0;
}
.offre-drawer__meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}
.offre-drawer__meta dt {
  font-size: 0.75rem;
  color: var(--color-muted, #6b7280);
}
.offre-drawer__meta dd {
  margin: 0;
  font-weight: 500;
}
.offre-drawer__body section h3 {
  font-size: 0.95rem;
  margin: 0 0 0.5rem 0;
}
.offre-drawer__body ul {
  margin: 0;
  padding-left: 1.25rem;
}
.offre-drawer__format {
  font-size: 0.8rem;
  color: var(--color-muted, #6b7280);
}
.offre-drawer__external {
  color: var(--color-accent, #16a34a);
  font-size: 0.9rem;
}
.offre-drawer__footer {
  padding: 1rem 1.25rem;
  border-top: 1px solid var(--color-border, #e5e7eb);
}
.btn-primary {
  display: inline-block;
  padding: 0.7rem 1.2rem;
  background: var(--color-accent, #16a34a);
  color: white;
  border-radius: 0.5rem;
  text-decoration: none;
  font-weight: 500;
}
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 200ms ease;
}
.drawer-enter-active .offre-drawer__panel,
.drawer-leave-active .offre-drawer__panel {
  transition: transform 200ms ease;
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-enter-from .offre-drawer__panel,
.drawer-leave-to .offre-drawer__panel {
  transform: translateX(100%);
}
</style>
