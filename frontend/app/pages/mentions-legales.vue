<script setup lang="ts">
// Page /mentions-legales — page légale publique référencée par layouts/public.vue.
definePageMeta({
  layout: "public",
  public: true,
  title: "Mentions légales",
})
</script>

<template>
  <article
    class="mx-auto max-w-3xl px-4 py-10 prose prose-slate"
    data-testid="page-mentions-legales"
  >
    <h1>Mentions légales</h1>

    <h2>Éditeur</h2>
    <p>
      ESG Mefali — plateforme conversationnelle de finance verte pour PME ouest-africaines.
      Pour toute demande, contactez-nous via la page <NuxtLink to="/contact">Contact</NuxtLink>.
    </p>

    <h2>Hébergement</h2>
    <p>
      L'application est hébergée en Europe ou en Afrique de l'Ouest, conformément aux exigences
      RGPD, UEMOA 20/2010 et à la loi ivoirienne 2013-450 sur la protection des données.
    </p>

    <h2>Propriété intellectuelle</h2>
    <p>
      L'ensemble des contenus présentés sur cette plateforme (textes, illustrations, logos,
      référentiels) est protégé par le droit d'auteur. Toute reproduction non autorisée est
      interdite.
    </p>

    <h2>Responsabilité</h2>
    <p>
      Les informations financières et ESG produites par l'IA sont des aides à la décision et
      n'engagent pas la responsabilité de l'éditeur. Les valeurs monétaires affichées sont
      indicatives et doivent être validées avec votre conseiller.
    </p>

    <h2>Cookies & traçage</h2>
    <p>
      Voir la page <NuxtLink to="/confidentialite">Confidentialité</NuxtLink> pour les détails
      sur la gestion des cookies et des consentements.
    </p>
  </article>
</template>
