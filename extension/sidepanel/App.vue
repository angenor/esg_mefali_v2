<script setup lang="ts">
// F52 US4 — Sidepanel orchestrator. Header + router custom + 3 views.
import { onMounted, onUnmounted, ref } from "vue"
import PanelHeader from "./components/PanelHeader.vue"
import ActiveCandidaturesView from "./views/ActiveCandidaturesView.vue"
import RecommendedOffersView from "./views/RecommendedOffersView.vue"
import MiniChatView from "./views/MiniChatView.vue"
import { fetchSidepanelContext, ApiError, type SidepanelContext } from "./lib/api"
import { onIncoming, sendToBackground } from "./lib/messaging"
import { DEFAULT_ROUTE, isValidRoute, type RouteId } from "./routes"

type PanelStatus = "loading" | "ready" | "auth_required" | "error"

const status = ref<PanelStatus>("loading")
const route = ref<RouteId>(DEFAULT_ROUTE)
const context = ref<SidepanelContext>({
  matched_offer_ids: [],
  active_candidatures: [],
  recommended_offers: [],
})
const errorMessage = ref<string | null>(null)

function navigate(target: string): void {
  if (isValidRoute(target)) route.value = target
}

function currentTabUrl(): { host: string; path: string } | null {
  // Sidepanel n'a pas accès direct à l'onglet ; on tente l'API chrome.tabs.
  return null
}

async function loadContextFromBackgroundOrFetch(): Promise<void> {
  status.value = "loading"
  errorMessage.value = null
  // Premier essai : récupérer via l'API directement avec l'URL passée par
  // le background dans les query params (?host=...&path=...).
  const params = new URLSearchParams(window.location.search)
  const host = params.get("host") ?? currentTabUrl()?.host ?? ""
  const path = params.get("path") ?? currentTabUrl()?.path ?? "/"
  if (!host) {
    status.value = "ready"
    return
  }
  try {
    const ctx = await fetchSidepanelContext(host, path)
    context.value = ctx
    status.value = "ready"
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      status.value = "auth_required"
    } else {
      status.value = "error"
      errorMessage.value = err instanceof Error ? err.message : "load_failed"
    }
  }
}

function openCandidature(id: string): void {
  void sendToBackground({ type: "OPEN_CANDIDATURE", payload: { id } }).catch(
    () => undefined
  )
}

let unsubscribe: (() => void) | null = null

onMounted(() => {
  void loadContextFromBackgroundOrFetch()
  unsubscribe = onIncoming((msg) => {
    if (msg.type === "CONTEXT_READY") {
      context.value = msg.payload
      status.value = "ready"
    } else if (msg.type === "AUTH_REQUIRED") {
      status.value = "auth_required"
    }
  })
})

onUnmounted(() => {
  if (unsubscribe) unsubscribe()
})
</script>

<template>
  <main class="flex min-h-screen flex-col bg-white text-slate-900" data-testid="sidepanel-app">
    <PanelHeader :current-route="route" @navigate="navigate" />

    <div v-if="status === 'loading'" class="px-3 py-3 text-xs text-slate-500" data-testid="status-loading">
      Chargement…
    </div>
    <div v-else-if="status === 'auth_required'" class="px-3 py-3 text-xs text-slate-700" data-testid="status-auth">
      <p>Veuillez vous connecter à ESG Mefali pour activer le panneau.</p>
      <a
        class="mt-2 inline-block rounded bg-emerald-600 px-2 py-1 text-xs font-medium text-white"
        href="https://app.esg-mefali.example/login"
        target="_blank"
        rel="noopener"
      >
        Ouvrir la plateforme
      </a>
    </div>
    <div v-else-if="status === 'error'" class="px-3 py-3 text-xs text-red-700" data-testid="status-error">
      {{ errorMessage ?? "Échec du chargement." }}
    </div>
    <template v-else>
      <ActiveCandidaturesView
        v-if="route === 'candidatures'"
        :items="context.active_candidatures"
        @open="openCandidature"
      />
      <RecommendedOffersView
        v-else-if="route === 'offers'"
        :items="context.recommended_offers"
      />
      <MiniChatView v-else-if="route === 'chat'" />
    </template>
  </main>
</template>
