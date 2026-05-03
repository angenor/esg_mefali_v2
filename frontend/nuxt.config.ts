import tailwindcss from "@tailwindcss/vite";

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "2025-04-01",
  devtools: { enabled: true },

  modules: ["@pinia/nuxt", "nuxt-security"],

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
