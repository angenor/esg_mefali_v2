<script setup lang="ts">
// F42 T074 — Témoignage anonymisé page publique
import { useT } from "~/composables/useT"
const { t } = useT()
</script>

<template>
  <section class="bg-slate-50 py-16">
    <figure class="mx-auto max-w-3xl px-6 text-center">
      <blockquote class="text-xl font-medium leading-relaxed text-slate-800 md:text-2xl">
        {{ t("public.testimonial.quote") }}
      </blockquote>
      <figcaption class="mt-6 text-sm text-slate-600">
        {{ t("public.testimonial.attribution") }}
      </figcaption>
    </figure>
  </section>
</template>
