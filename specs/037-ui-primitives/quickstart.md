# Quickstart — UI Primitives Library (F37)

Spec : [spec.md](./spec.md) · Plan : [plan.md](./plan.md) · Date : 2026-05-02

## 1. Pré-requis

- F36 (design tokens) mergée — `frontend/app/assets/css/tokens.css` disponible.
- Stack frontend installée : `make setup` puis `make frontend` (port 3001).

## 2. Installer les nouvelles dépendances

```bash
cd frontend
pnpm add @floating-ui/vue dompurify vee-validate @vee-validate/zod zod
pnpm add -D @types/dompurify @testing-library/vue axe-core
```

## 3. Conventions à respecter (rappel court)

- Tout nouvel atome vit sous `frontend/app/components/ui/Ui<Name>.vue`.
- Auto-import Nuxt 4 sous le préfixe `Ui` — rien à déclarer dans `nuxt.config.ts`.
- Aucune valeur visuelle en dur : couleur / espacement / radius / ombre / motion ⇒ tokens F36.
- Pas de `v-html` brut ⇒ `import { sanitizeHtml } from '~/utils/sanitize'`.
- Animations gsap ⇒ `useReducedMotion()` + `gsapDuration(d, reduced)` (déjà disponible).

## 4. Consommer un atome dans une page

```vue
<script setup lang="ts">
import { ref } from 'vue'
const email = ref('')
const loading = ref(false)
async function onSubmit() {
  loading.value = true
  try { /* … */ } finally { loading.value = false }
}
</script>

<template>
  <form @submit.prevent="onSubmit" class="space-y-4">
    <UiFormField label="Email" required helper="Votre email professionnel">
      <UiInput v-model="email" type="email" placeholder="vous@entreprise.ci" />
    </UiFormField>

    <UiButton type="submit" :loading="loading">Se connecter</UiButton>
  </form>
</template>
```

## 5. Utiliser les toasts (impératif)

```ts
const toast = useToast()
toast.push({ severity: 'success', message: 'Profil enregistré.' })
toast.push({
  severity: 'error',
  message: 'Sauvegarde impossible.',
  actionLabel: 'Réessayer',
  onAction: retry,
})
```

Le `<UiToastHost />` doit être monté une fois dans `app.vue`.

## 6. Lancer la showcase `/dev/components`

```bash
make frontend          # http://localhost:3001
# puis ouvrir http://localhost:3001/dev/components
```

La page est gardée par un middleware DEV-only ; elle renvoie 404 en production.

## 7. Lancer les tests d'atomes

```bash
cd frontend
pnpm vitest run tests/unit/ui                 # tous les atomes
pnpm vitest run tests/unit/ui/UiButton.spec.ts
pnpm vitest run --coverage                    # vérifie ≥ 80 % (SC-005)
```

Audit a11y automatisé sur la showcase :

```bash
pnpm vitest run tests/integration/showcase-a11y.spec.ts
```

## 8. Audit manuel d'a11y (SC-009)

Sur Modal et Combobox au minimum :

1. macOS : Cmd+F5 pour activer VoiceOver, ouvrir une Modal, vérifier annonce du titre, navigation Tab (cycle), `Esc` ferme et restaure le focus.
2. Sur un Combobox, vérifier annonce des options à la frappe, sélection au Enter, fermeture au Esc.

Documenter les résultats dans une note de session ou un commentaire de PR.

## 9. Que NE PAS faire

- Importer une lib UI tierce (PrimeVue, Vuetify, shadcn-vue, radix-vue, …) — bloqué en revue.
- Ajouter un composant qui fait un appel réseau dans son template.
- Mettre une bottom-sheet ici (c'est F39).
- Faire un breaking change d'API sans mettre à jour `contracts/` + `data-model.md` + PR de migration.

## 7bis. Bundle JS imputable aux primitives (SC-006)

Mesure imposée : ≤ 60 kB gzipped pour la part F37 sur `/login` après refonte F38.

> **Statut 2026-05-03** : non mesurable à ce stade — `/login` n'est pas encore migré sur les primitives F37 (la migration appartient à F38 « App Shell, Layout & Navigation »). La mesure sera produite à la livraison de F38 :
>
> ```bash
> cd frontend
> pnpm build && du -ksh .output/public/_nuxt/*.js | sort -h
> # ou
> pnpm dlx nuxt analyze
> ```
>
> Comparer la taille avant/après refonte. Si > 60 kB gzipped, identifier l'atome lourd (probablement `UiCombobox` virtualisation ou `UiFileUpload` aperçu image) et appliquer un découpage code-splitting.

## 8bis. Audit manuel clavier + tap targets (SC-003 / SC-004)

Voir la check-list dédiée : [`frontend/tests/integration/showcase-keyboard.manual.md`](../../frontend/tests/integration/showcase-keyboard.manual.md).

## 8ter. Lecteur d'écran (SC-009)

Voir [`frontend/tests/integration/screenreader-a11y.manual.md`](../../frontend/tests/integration/screenreader-a11y.manual.md).

## 10. Ressources

- [`spec.md`](./spec.md) — exigences fonctionnelles et critères de succès.
- [`research.md`](./research.md) — décisions techniques et alternatives rejetées.
- [`data-model.md`](./data-model.md) — récapitulatif tabulaire des 27 atomes.
- [`contracts/component-api.md`](./contracts/component-api.md) — conventions transverses figées.
- [`contracts/critical-atoms.md`](./contracts/critical-atoms.md) — détails par atome critique.
- F36 tokens : `frontend/app/assets/css/tokens.css`.
