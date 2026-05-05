<script setup lang="ts">
// F49 T041/T046/T047/T048/T053 — page publique /verify/[id].
//
// SSR Nuxt : on récupère `GET {apiBase}/verify/{id}/json` côté serveur,
// on règle 404 si non trouvé, on injecte `Cache-Control` + `Content-Language`,
// puis on rend la page (badge ✓/✗, identité, KPI, sources). Aucun lien retour
// vers l'app PME (P7). Page lisible sans JS (rendu HTML serveur complet).
import { computed, ref } from "vue"
import { appendResponseHeader, setResponseStatus } from "h3"
import SignatureBadge from "~/components/rapports/verify/SignatureBadge.vue"
import RevokedBanner from "~/components/rapports/verify/RevokedBanner.vue"
import PayloadView from "~/components/rapports/verify/PayloadView.vue"
import PublicFooter from "~/components/rapports/verify/PublicFooter.vue"
import LangSwitch from "~/components/rapports/verify/LangSwitch.vue"
import { useVerifyI18n, type VerifyLang } from "~/composables/useVerifyI18n"
import type {
  PublicVerification,
  PublicIndicator,
  PublicSource,
  RevokeReason,
  AttestationStatus,
} from "~/types/attestations"

// Forme brute renvoyée par le backend F30 (cf. backend/app/attestations/schemas.py).
interface BackendPublicVerification {
  public_id: string
  status: AttestationStatus
  entreprise_name: string
  generated_at: string
  valid_until: string
  revoked_at: string | null
  revoke_reason: string | null
  scores: Record<string, unknown>
  referentiels_versions: Record<string, string>
  hash_document: string
  signature_ed25519: string
  pubkey_fingerprint: string
  download_url: string
  indicators?: PublicIndicator[]
}

function adapt(raw: BackendPublicVerification | null | undefined):
  | PublicVerification
  | null {
  if (!raw) return null
  // Sources : F30 ne les expose pas encore au top-level — on collecte les
  // `source_id` cités par les indicators et on synthétise des entrées minimales.
  const indicators: PublicIndicator[] = raw.indicators ?? []
  const seen = new Set<string>()
  const sources: PublicSource[] = []
  for (const i of indicators) {
    if (i.source_id && !seen.has(i.source_id)) {
      seen.add(i.source_id)
      sources.push({ id: i.source_id, title: i.source_id, url: null })
    }
  }
  return {
    public_id: raw.public_id,
    entity_legal_name: raw.entreprise_name,
    status: raw.status,
    issued_at: raw.generated_at,
    expires_at: raw.valid_until,
    revoked_at: raw.revoked_at,
    revoke_reason: (raw.revoke_reason as RevokeReason | null) ?? null,
    // F30 n'expose pas encore `signature_valid` ; on déduit de la présence
    // d'une signature non vide. La vérification cryptographique côté backend
    // se fera dans une itération ultérieure (cf. F30 backlog).
    signature_valid: Boolean(raw.signature_ed25519),
    payload: { indicators, sources },
    download_url: raw.download_url,
  }
}

definePageMeta({
  layout: "public",
  public: true,
  title: "Vérification d'attestation",
})

const route = useRoute()
const id = computed(() => String(route.params.id))
const config = useRuntimeConfig()
const apiBase = String(config.public.apiBase ?? "").replace(/\/$/, "")

// Lecture du cookie côté SSR pour initialiser la langue sans flash FR/EN.
// On utilise un ref Vue local pour que le template soit réactif aux changements.
const langCookie = useCookie<VerifyLang>("mefali_verify_lang", {
  default: () => "fr",
  sameSite: "lax",
  maxAge: 60 * 60 * 24 * 365,
})
const lang = ref<VerifyLang>(langCookie.value === "en" ? "en" : "fr")

const { t, dateFormatter } = useVerifyI18n(lang)

const { data: raw, error } = await useFetch<BackendPublicVerification>(
  () => `${apiBase}/verify/${id.value}/json`,
  {
    key: `verify-${id.value}`,
    server: true,
    credentials: "omit",
  },
)

const data = computed<PublicVerification | null>(() => adapt(raw.value))

// Headers SSR — cache CDN court + langue. `appendResponseHeader` et
// `setResponseStatus` sont auto-importés depuis h3 dans le contexte SSR Nuxt 4.
if (import.meta.server) {
  const event = useRequestEvent()
  if (event) {
    appendResponseHeader(
      event,
      "Cache-Control",
      "public, max-age=0, s-maxage=60, stale-while-revalidate=60",
    )
    appendResponseHeader(event, "Content-Language", lang.value)
    if (error.value || !raw.value) {
      setResponseStatus(event, 404)
    }
  }
}

const isError = computed(() => Boolean(error.value) || !data.value)
const status = computed(() => data.value?.status ?? null)
const signatureValid = computed(() => Boolean(data.value?.signature_valid))

const titleText = computed(() => {
  if (!data.value) return t("errors.not_found_title")
  return `${t("header.title")} — ${data.value.entity_legal_name}`
})

const description = computed(() => {
  if (!data.value) return t("errors.not_found_body")
  return `${data.value.entity_legal_name} — ${t("header.subtitle")}`
})

const ogImage = computed(() => `${apiBase}/static/og-verify.png`)

useHead({
  title: titleText,
  htmlAttrs: { lang },
  meta: [
    { name: "description", content: description },
    { name: "robots", content: "noindex,nofollow" },
    { property: "og:title", content: titleText },
    { property: "og:description", content: description },
    { property: "og:image", content: ogImage },
    { property: "og:type", content: "website" },
  ],
})

const jsonLd = computed(() => {
  if (!data.value) return null
  return {
    "@context": "https://schema.org",
    "@type": "Certification",
    name: titleText.value,
    issuedBy: {
      "@type": "Organization",
      name: "ESG Mefali",
    },
    about: {
      "@type": "Organization",
      name: data.value.entity_legal_name,
    },
    validFrom: data.value.issued_at,
    expires: data.value.expires_at,
    identifier: data.value.public_id,
  }
})

function setLang(next: VerifyLang) {
  lang.value = next
  langCookie.value = next
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return ""
  return dateFormatter.value(iso)
}
</script>

<template>
  <article class="mx-auto max-w-3xl px-4 py-8" data-testid="verify-page">
    <header class="mb-6 flex items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">
          {{ t("header.title") }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">{{ t("header.subtitle") }}</p>
      </div>
      <LangSwitch :lang="lang" @update:lang="setLang" />
    </header>

    <section
      v-if="isError"
      class="rounded-lg border border-gray-200 bg-white p-6"
      data-testid="verify-error"
    >
      <h2 class="text-lg font-semibold text-gray-900">
        {{ t("errors.not_found_title") }}
      </h2>
      <p class="mt-2 text-sm text-gray-600">
        {{ t("errors.not_found_body") }}
      </p>
      <p class="mt-2 text-xs text-gray-500">
        <span class="font-mono">{{ id }}</span>
      </p>
      <p class="mt-4">
        <a href="/about" class="text-brand-600 hover:underline">
          {{ t("footer.about") }}
        </a>
      </p>
    </section>

    <template v-else-if="data">
      <RevokedBanner
        v-if="data.revoked_at"
        :revoked-at="data.revoked_at"
        :reason="data.revoke_reason"
        :lang="lang"
        class="mb-6"
      />

      <section class="mb-6 flex flex-wrap items-center gap-3">
        <SignatureBadge :valid="signatureValid" :lang="lang" />
        <span
          class="rounded-full px-3 py-1 text-xs font-semibold"
          :class="{
            'bg-green-50 text-green-700': status === 'active',
            'bg-yellow-50 text-yellow-700': status === 'expired',
            'bg-red-50 text-red-700': status === 'revoked',
          }"
          data-testid="status-chip"
        >
          {{ t(`status.${status}`) }}
        </span>
      </section>

      <section
        class="mb-6 rounded-lg border border-gray-200 bg-white p-4"
        data-testid="identity-block"
      >
        <dl class="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt class="text-xs uppercase text-gray-500">
              {{ t("identity.legal_name") }}
            </dt>
            <dd class="mt-0.5 font-semibold text-gray-900">
              {{ data.entity_legal_name }}
            </dd>
          </div>
          <div v-if="data.type">
            <dt class="text-xs uppercase text-gray-500">
              {{ t("identity.type") }}
            </dt>
            <dd class="mt-0.5 text-gray-900">
              {{ t(`attestation_type.${data.type}`) }}
            </dd>
          </div>
          <div>
            <dt class="text-xs uppercase text-gray-500">
              {{ t("identity.issued_at") }}
            </dt>
            <dd class="mt-0.5 text-gray-900">{{ fmtDate(data.issued_at) }}</dd>
          </div>
          <div>
            <dt class="text-xs uppercase text-gray-500">
              {{ t("identity.expires_at") }}
            </dt>
            <dd class="mt-0.5 text-gray-900">{{ fmtDate(data.expires_at) }}</dd>
          </div>
        </dl>
        <p v-if="data.download_url" class="mt-4">
          <a
            :href="data.download_url"
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-800 hover:bg-gray-50"
            data-testid="download-pdf"
          >
            ↓ {{ t("actions.download_pdf") }}
          </a>
        </p>
      </section>

      <PayloadView
        :indicators="data.payload?.indicators ?? []"
        :sources="data.payload?.sources ?? []"
        :lang="lang"
      />

      <aside
        class="mt-8 rounded-lg border border-brand-200 bg-brand-50 p-4 text-sm text-brand-900"
        data-testid="explainer"
      >
        <h3 class="font-semibold">{{ t("explainer.title") }}</h3>
        <p class="mt-1">{{ t("explainer.body") }}</p>
        <p class="mt-2">
          <a href="/about" class="text-brand-700 underline">
            {{ t("explainer.doc_link") }}
          </a>
        </p>
      </aside>

      <component
        :is="'script'"
        v-if="jsonLd"
        type="application/ld+json"
        v-html="JSON.stringify(jsonLd)"
      />
    </template>
  </article>

  <PublicFooter :lang="lang" />
</template>
