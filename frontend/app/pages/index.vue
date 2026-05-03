<script setup lang="ts">
// F38 T030 — page d'accueil publique
definePageMeta({
  layout: "public",
  public: true,
  title: "Accueil",
})
const { data, pending, error } = useHealth();

const statut = computed(() => {
  if (pending.value) return "Chargement…";
  if (error.value || !data.value) return "Backend indisponible";
  return data.value.status === "ok" ? "Backend OK" : "Backend indisponible";
});

const couleur = computed(() =>
  statut.value === "Backend OK" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800",
);
</script>

<template>
  <main class="min-h-screen flex items-center justify-center bg-slate-50 p-6">
    <section class="max-w-md w-full bg-white shadow rounded-2xl p-8 text-center">
      <h1 class="text-2xl font-semibold text-slate-900">ESG Mefali</h1>
      <p class="mt-2 text-sm text-slate-500">
        Plateforme ESG &amp; financement pour PME ouest-africaines.
      </p>
      <div :class="['mt-6 inline-block px-4 py-2 rounded-lg text-sm font-medium', couleur]">
        {{ statut }}
      </div>
      <p class="mt-4 text-xs text-slate-400">
        Sonde
        <code class="px-1 py-0.5 bg-slate-100 rounded">GET /health</code>
      </p>
    </section>
  </main>
</template>
