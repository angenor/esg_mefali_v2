# Implementation Plan: Rapports PDF & Page publique /verify (UI F24 + F30)

**Branch**: `049-rapports-attestations-ui` | **Date**: 2026-05-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/049-rapports-attestations-ui/spec.md`

## Summary

Cette feature livre **deux pages Nuxt 4** côté frontend, qui exploitent les endpoints backend déjà implantés par F24 (rapports PDF) et F30 (attestations Ed25519 + page publique de vérification). Aucune nouvelle table ni nouveau endpoint backend n'est nécessaire — l'effort est purement UI/UX et SSR :

1. `pages/rapports/index.vue` (PME authentifiée) — table des rapports + table des attestations, drawer d'aperçu PDF, modale de génération avec progression SSE, modale de partage (lien + QR), modale de révocation (motif catégorisé).
2. `pages/verify/[id].vue` (publique, sans auth) — vitrine produit pour décideurs financiers : SSR avec cache CDN court (≤ 60 s) + invalidation explicite à la révocation, badge ✓/✗, lecture seule des KPI sourcés, bilingue FR/EN, no-JS fallback, Lighthouse ≥ 95.

L'approche technique :

- Réutiliser le layout `public.vue` (F38) déjà présent et la primitive UI / le design system (F36, F37, F40).
- Stores Pinia dédiés `useReportsStore`, `useAttestationsStore`.
- Génération de rapport pilotée via SSE (`EventSource`) avec un état persisté côté serveur pour permettre le rattrapage au retour (FR-003a).
- Aperçu PDF via URL signée à TTL court (≤ 5 min) pointée par une `<iframe>`, jamais d'URL permanente exposée.
- QR PNG côté front via la lib `qrcode` (déjà installée par F30).
- Sur la page publique : SSR Nuxt natif (`useFetch` côté serveur), `route rules` pour cache headers, `setResponseHeader('Cache-Control')` cohérent avec le CDN.

## Technical Context

**Language/Version** : TypeScript 5.x (Nuxt 4, Vue 3 Composition API), Python 3.12 (FastAPI déjà livré F24/F30).
**Primary Dependencies** : Nuxt 4, Pinia, Tailwind v4, gsap (modales/drawer), `qrcode` (QR), `pdf.js` lazy-load (aperçu inline avec fallback iframe natif), `@nuxtjs/i18n` ou composable interne pour la bascule FR/EN.
**Storage** : aucune nouvelle table ; lecture sur `Rapport`, `Attestation` (déjà créées par F24/F30, RLS active).
**Testing** : vitest (unit/component) sur stores et composants ; Playwright pour 2 parcours E2E (génération-rapport + verify-public). Backend déjà couvert par F24/F30.
**Target Platform** : navigateurs modernes (Chrome/Edge/Safari/Firefox) ; mobile-first ; SSR Nuxt côté Node.
**Project Type** : web application (frontend + backend déjà existant).
**Performance Goals** : `/verify/{id}` LCP < 1,2 s sur 4G ; Lighthouse ≥ 95 ; QR scannable à 30 cm sur 5 modèles.
**Constraints** : SSR obligatoire `/verify` (FR-015) ; no-JS fallback (FR-016) ; cache CDN ≤ 60 s + invalidation explicite (FR-015 + SC-009) ; URL aperçu PDF signée ≤ 5 min (FR-002) ; multi-tenant 404 (P2).
**Scale/Scope** : 2 nouvelles pages, ~8 composants, 2 stores Pinia, 0 nouveau endpoint backend, 0 nouvelle table.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | KPI affichés sur `/verify` portent un repère de source (FR-013 + composant `VizSourcePin` existant F40) | ✅ |
| P2 | Multi-tenant RLS | Aucun nouveau modèle ; lecture passe par les endpoints `/me/...` (RLS active sur `account_id`) ; URL aperçu PDF signée tenant-bound | ✅ |
| P3 | Audit log append-only | Révocation déclenche déjà l'écriture audit côté backend F30 ; UI ne fait que poster `/me/attestations/{id}/revoke` | ✅ |
| P4 | Versioning + snapshot | Pas de référentiel modifié ici ; snapshot candidature non touché | ✅ (N/A) |
| P5 | Money typé | Aucun montant traité dans cette UI (les rapports embarquent leurs propres `Money` côté backend) | ✅ (N/A) |
| P6 | Pivot Indicateur unique | Aucun stockage ESG nouveau ; lecture seule | ✅ (N/A) |
| P7 | Plateforme fermée aux intermédiaires | Partage = URL `/verify/{id}` + QR uniquement, jamais de webhook ; page publique sans auth, sans lien retour | ✅ |
| P8 | Édition manuelle + sync LLM | Cette feature ne crée pas de champ LLM-only ; révocation = action humaine | ✅ (N/A) |
| P9 | Tool-use LLM fiable | Pas de nouveau tool LLM dans cette feature | ✅ (N/A) |
| P10 | UX bottom sheet | Modales de génération / partage / révocation suivent le pattern bottom sheet ou modale-écran selon le runtime existant (jamais inline dans une bulle LLM puisque cette page n'est pas conversationnelle) | ✅ |

### Contraintes techniques (rappel)

- Stack : Nuxt 4 + Tailwind v4 + Pinia côté front ; FastAPI Python 3.12 côté back (déjà livré).
- Hébergement Europe / Afrique de l'Ouest uniquement.
- Conformité RGPD + UEMOA + 2013-450 dès le MVP (footer mentions + lien `/about`).
- Langue : FR par défaut sur PME ; bilingue FR/EN limité à `/verify/{id}` (P10 exception : éligible internationaux).

## Project Structure

### Documentation (this feature)

```text
specs/049-rapports-attestations-ui/
├── plan.md              # ce fichier
├── research.md          # Phase 0
├── data-model.md        # Phase 1 — entités UI dérivées (lecture seule)
├── quickstart.md        # Phase 1 — comment lancer + tester
├── contracts/           # Phase 1 — contrats UI ↔ backend (réutilisés F24/F30)
└── tasks.md             # Phase 2 (généré par /speckit-tasks)
```

### Source Code (repository root)

```text
frontend/app/
├── pages/
│   ├── rapports/
│   │   └── index.vue                  # NEW — liste rapports + attestations (US1, US3)
│   └── verify/
│       └── [id].vue                   # MODIFIED — remplace le stub F38 (US4, US5, US6)
├── components/
│   └── rapports/                      # NEW directory
│       ├── ReportTable.vue
│       ├── ReportDrawer.vue
│       ├── GenerateReportModal.vue
│       ├── AttestationTable.vue
│       ├── ShareAttestationModal.vue
│       ├── RevokeAttestationModal.vue
│       └── verify/
│           ├── SignatureBadge.vue
│           ├── RevokedBanner.vue
│           ├── PayloadView.vue
│           ├── LangSwitch.vue
│           └── PublicFooter.vue
├── stores/
│   ├── reports.ts                     # NEW
│   └── attestations.ts                # NEW
├── composables/
│   ├── useReportGenerationStream.ts   # NEW — SSE wrapper + reconnect
│   ├── useSignedPdfUrl.ts             # NEW — fetch URL signée TTL court
│   └── useVerifyI18n.ts               # NEW — bilingue FR/EN scope contrôlé
└── i18n/
    └── verify/
        ├── fr.json                    # NEW
        └── en.json                    # NEW

frontend/tests/
├── unit/
│   ├── stores/reports.test.ts
│   └── stores/attestations.test.ts
├── component/
│   ├── ReportTable.test.ts
│   ├── GenerateReportModal.test.ts
│   └── verify/SignatureBadge.test.ts
└── e2e/
    ├── rapports-generation.spec.ts
    └── verify-public.spec.ts

backend/                               # AUCUN changement (F24+F30 suffisants)
```

**Structure Decision** : web application en monorepo, tout le travail dans `frontend/app`. Backend reste intact.

## Phase 0 — Research

Voir [research.md](./research.md). Sujets résolus :

1. SSR Nuxt + cache CDN court avec invalidation explicite à la révocation.
2. SSE depuis Nuxt côté front avec rattrapage au retour de page.
3. Aperçu PDF via URL signée (pattern existant côté backend F24).
4. QR code PNG côté front (lib `qrcode`).
5. No-JS fallback pour `/verify/{id}` (rendu HTML statique côté serveur).
6. Bilingue scope contrôlé : statiques + énumérations seulement.
7. Lighthouse ≥ 95 sur page mobile : techniques (preload, fonts, no-JS, schémas structurés).

Toutes les `NEEDS CLARIFICATION` ont été résolues lors de `/speckit-clarify` (5 questions, voir spec.md → Clarifications).

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md) — entités UI dérivées (lecture seule depuis F24/F30) + états de la machine de génération de rapport côté UI.
- [contracts/](./contracts/) — contrats UI ↔ backend réutilisés (F24/F30) + nouveau besoin éventuel d'URL signée pour aperçu PDF.
- [quickstart.md](./quickstart.md) — instructions pour lancer et tester la feature en local (3 terminaux, scénarios manuels).

### Constitution re-check post-design

Aucun écart introduit. Tous les gates restent ✅. Aucune entrée dans `Complexity Tracking`.

## Complexity Tracking

> Aucune violation à justifier.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
