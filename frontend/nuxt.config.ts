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
        "connect-src": ["'self'", "http://localhost:8000"],
      },
    },
  },

  css: ["~/assets/css/main.css"],

  vite: {
    plugins: [tailwindcss()],
  },

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || "http://localhost:8000",
    },
  },

  app: {
    head: {
      htmlAttrs: { lang: "fr" },
      title: "ESG Mefali",
    },
  },
});
