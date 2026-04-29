<script setup lang="ts">
/**
 * F03 US4 — Page démo SC-003 : 3 instances <SourceCite> avec statuts différents.
 *
 * Les UUIDs sont des exemples — remplacer par des UUID réels en environnement
 * dev seedé (cf. backend/app/scripts/seed_admin.py + insert sources de test).
 */
import SourceCite from '../../components/source/SourceCite.vue'

const demos = [
  { label: 'Source vérifiée (verified)', ids: ['11111111-1111-1111-1111-111111111111'] },
  { label: 'Source en attente (pending)', ids: ['22222222-2222-2222-2222-222222222222'] },
  { label: 'Source obsolète (outdated)', ids: ['33333333-3333-3333-3333-333333333333'] },
]
</script>

<template>
  <main class="demo-page">
    <h1>Démo &lt;SourceCite&gt; (F03 US4)</h1>
    <p>
      Cliquez sur le picto pour ouvrir le bottom sheet listant la source.
      Selon le statut renvoyé par <code>GET /sources/&#123;id&#125;</code>,
      le badge change.
    </p>

    <ul>
      <li v-for="d in demos" :key="d.label">
        <span>{{ d.label }} — </span>
        <SourceCite :source-ids="d.ids" />
      </li>
    </ul>
  </main>
</template>

<style scoped>
.demo-page { max-width: 720px; margin: 2rem auto; padding: 0 1rem; }
ul { list-style: none; padding: 0; }
li { margin: 1rem 0; }
</style>
