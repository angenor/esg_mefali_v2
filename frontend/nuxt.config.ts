import tailwindcss from "@tailwindcss/vite";

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "2025-04-01",
  devtools: { enabled: true },

  modules: ["@pinia/nuxt", "nuxt-security"],

  // F48 fix — /credit-score formate des Date via Intl.DateTimeFormat (GaugeHero,
  // RecalcStrip, ScoreHistoryChart). Sans timezone fixe, le rendu serveur diverge
  // du client → hydration text-content mismatch → event listeners @click du
  // EmptyStateWizard non attachés. La page exige déjà JWT cookie + EventBus
  // client + localStorage wizard : le SSR n'apporte aucun bénéfice ici.
  // Précédent F47 (commit c14899e).
  routeRules: {
    "/credit-score": { ssr: false },
    // F49 T005 — page publique /verify : SSR + cache CDN court (≤ 60 s)
    // avec stale-while-revalidate. L'invalidation explicite du CDN à la
    // révocation est gérée côté backend (cf. T010).
    "/verify/**": {
      swr: 60,
      headers: {
        "Cache-Control":
          "public, max-age=0, s-maxage=60, stale-while-revalidate=60",
      },
    },
  },

  // F02 — Sécurité : headers HSTS, CSP minimal, X-Frame-Options, cookies par défaut.
  security: {
    headers: {
      strictTransportSecurity: {
        maxAge: 15552000,
        includeSubdomains: true,
      },
      xFrameOptions: "DENY",
      contentSecurityPolicy: {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-inline'"],
        "style-src": ["'self'", "'unsafe-inline'"],
        "img-src": ["'self'", "data:"],
        "connect-src": ["'self'", "http://localhost:8000", "http://localhost:8010"],
      },
    },
  },

  css: ["~/assets/css/main.css", "~/assets/css/leaflet.css"],

  vite: {
    plugins: [tailwindcss()],
  },

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || "http://localhost:8010",
      // Désactivation temporaire du bandeau de vérification email pour les tests.
      // Override via `NUXT_PUBLIC_DISABLE_EMAIL_VERIFICATION=false`. Default: true.
      disableEmailVerification:
        process.env.NUXT_PUBLIC_DISABLE_EMAIL_VERIFICATION ?? "true",
      // F45 T071 — Export PDF du plan d'action (différé jusqu'à F51).
      featurePlanExportPdf:
        process.env.NUXT_PUBLIC_FEATURE_PLAN_EXPORT_PDF ?? "false",
    },
  },

  app: {
    head: {
      htmlAttrs: { lang: "fr" },
      title: "ESG Mefali",
      link: [
        {
          rel: "preload",
          as: "font",
          type: "font/woff2",
          href: "/fonts/Inter-Regular.woff2",
          crossorigin: "anonymous",
        },
        { rel: "icon", type: "image/svg+xml", href: "/brand/symbol.svg" },
        { rel: "alternate icon", type: "image/x-icon", href: "/favicon.ico" },
        { rel: "apple-touch-icon", sizes: "180x180", href: "/apple-touch-icon.png" },
      ],
    },
  },
});
