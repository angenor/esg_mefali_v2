<script setup lang="ts">
// Page /confidentialite — politique de confidentialité publique référencée par layouts/public.vue.
definePageMeta({
  layout: "public",
  public: true,
  title: "Confidentialité",
})
</script>

<template>
  <article
    class="mx-auto max-w-3xl px-4 py-10 prose prose-slate"
    data-testid="page-confidentialite"
  >
    <h1>Politique de confidentialité</h1>

    <h2>Données collectées</h2>
    <p>
      ESG Mefali collecte uniquement les données nécessaires à l'évaluation ESG, au scoring
      financier et à la production de candidatures de financement. Les données sensibles sont
      stockées chiffrées dans une base PostgreSQL avec isolation par tenant (RLS).
    </p>

    <h2>Finalités du traitement</h2>
    <ul>
      <li>Calcul du scoring ESG multi-référentiels et du scoring de crédit.</li>
      <li>Génération de rapports de conformité et d'attestations vérifiables.</li>
      <li>Mise en relation avec les fonds et intermédiaires financiers (matching).</li>
      <li>Suivi des candidatures et notifications utilisateur.</li>
    </ul>

    <h2>Vos droits</h2>
    <p>
      Conformément au RGPD, à la loi UEMOA 20/2010 et à la loi ivoirienne 2013-450, vous
      disposez d'un droit d'accès, de rectification, d'effacement et de portabilité.
      Vous pouvez exercer ces droits depuis la rubrique
      <NuxtLink to="/parametres/donnees">Paramètres → Mes données</NuxtLink>
      ou
      <NuxtLink to="/parametres/suppression">Suppression du compte</NuxtLink>.
    </p>

    <h2>Conservation</h2>
    <p>
      Les exports RGPD sont conservés 30 jours. Une demande de suppression de compte est
      exécutée 30 jours après la requête (annulable pendant ce délai).
    </p>

    <h2>Hébergement</h2>
    <p>
      Toutes les données sont hébergées en Europe ou en Afrique de l'Ouest. Aucun déploiement
      n'est effectué aux États-Unis ou dans une zone non couverte par une décision d'adéquation.
    </p>
  </article>
</template>
