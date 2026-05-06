<script setup lang="ts">
// Page /contact — page de contact publique référencée par layouts/public.vue.
definePageMeta({
  layout: "public",
  public: true,
  title: "Contact",
})
</script>

<template>
  <article
    class="mx-auto max-w-3xl px-4 py-10 prose prose-slate"
    data-testid="page-contact"
  >
    <h1>Contact</h1>

    <p>
      Une question sur la plateforme ESG Mefali, le scoring ESG, les candidatures de financement
      ou la gestion de vos données ? Nous sommes à votre écoute.
    </p>

    <section class="not-prose mt-8 grid gap-4 sm:grid-cols-2">
      <div class="rounded-lg border border-slate-200 bg-white p-5">
        <h2 class="text-base font-semibold text-slate-900">Support utilisateur</h2>
        <p class="mt-2 text-sm text-slate-700">
          Pour toute aide à l'utilisation, ouverture de compte ou question fonctionnelle.
        </p>
        <a
          class="mt-3 inline-flex text-sm font-medium text-emerald-700 hover:underline"
          href="mailto:support@esg-mefali.example"
        >
          support@esg-mefali.example
        </a>
      </div>

      <div class="rounded-lg border border-slate-200 bg-white p-5">
        <h2 class="text-base font-semibold text-slate-900">Données & confidentialité</h2>
        <p class="mt-2 text-sm text-slate-700">
          Pour exercer vos droits RGPD ou poser une question sur le traitement.
        </p>
        <a
          class="mt-3 inline-flex text-sm font-medium text-emerald-700 hover:underline"
          href="mailto:dpo@esg-mefali.example"
        >
          dpo@esg-mefali.example
        </a>
      </div>
    </section>

    <p class="mt-8 text-sm text-slate-600">
      Les utilisateurs déjà connectés peuvent aussi contacter le support depuis
      <NuxtLink to="/parametres" class="text-emerald-700 hover:underline">leur espace
      Paramètres</NuxtLink>.
    </p>
  </article>
</template>
