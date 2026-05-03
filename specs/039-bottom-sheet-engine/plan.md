# Implementation Plan: F39 — Bottom Sheet Engine (UI des tools `ask_*`)

**Branch**: `039-bottom-sheet-engine` | **Date**: 2026-05-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/039-bottom-sheet-engine/spec.md`

## Summary

Concrétiser la règle constitutionnelle **P10** côté frontend en fournissant un moteur unique de bottom sheet animé qui rend tous les tools d'interaction LLM (`ask_qcu`, `ask_qcm`, `ask_yes_no`, `ask_select`, `ask_number`, `ask_date`, `ask_date_range`, `ask_rating`, `ask_file_upload`, `show_form`, `show_summary_card`). Le moteur reçoit une instruction `{tool, payload, context}` issue d'un message tool non répondu du thread, monte le wrapper correspondant, désactive la barre de saisie texte, applique focus trap + reduced-motion, expose un bouton sticky « Répondre librement », et au submit poste côté backend un message structuré `{content: récap humain, payload_json, context_json}` consommable par F14. Reconstruction automatique au reload depuis le dernier message tool non répondu (DB = source de vérité, P8). Toute conversion FCFA↔EUR via peg fixe `655.957` (P5). Aucune persistance locale d'une saisie partielle.

Approche technique : Vue 3 Composition API + GSAP (déjà dans le projet) + Pinia store éphémère + génération zod depuis OpenAPI Pydantic au build (`pnpm gen:tools`). Les wrappers consomment exclusivement les primitives F37 existantes (`UiRadioGroup`, `UiCheckboxGroup`, `UiCombobox`, `UiNumber`, `UiDatePicker`, `UiDateRangePicker`, `UiFileUpload`, `UiButton`). Tests vitest + @testing-library/vue obligatoires par wrapper (rendu, validation, submit payload, ESC = bascule libre, XSS rendered as text).

## Technical Context

**Language/Version**: TypeScript 5.x (Nuxt 4 / Vue 3.5 Composition API)
**Primary Dependencies**: Nuxt 4, Pinia, GSAP 3.12, zod 3.23, vee-validate + @vee-validate/zod, dompurify 3.1, Tailwind v4. Aucune nouvelle dépendance runtime requise (toutes déjà présentes dans `frontend/package.json`).
**Storage**: Aucun stockage local persistant pour cette feature (contrainte issue de la clarification Q1). Lecture en cours d'instruction du dernier message tool non répondu via API existante du chat (F14/F15). État éphémère dans Pinia.
**Testing**: vitest + @testing-library/vue + happy-dom (déjà configurés). Tests par composant : rendu, validation, submit payload, ESC, focus trap, reduced motion, sanitize XSS. Tests d'intégration de l'orchestrateur sur un mock de thread.
**Target Platform**: Navigateurs evergreen (Chrome 110+, Firefox 110+, Safari 16+) ; mobile WebView (PWA) ; pas de support IE/legacy. Hébergement frontend Europe ou Afrique de l'Ouest (constitution).
**Project Type**: web (frontend Nuxt 4 dans `frontend/app/`, consomme l'API FastAPI déjà exposée par F15).
**Performance Goals**: Apparition perçue < 200 ms (NFR-001) ; scroll virtualisé liste 200 options à 60 fps (NFR-004 / SC-003) ; upload PDF 5 Mo < 5 s (SC-005).
**Constraints**: Bouton « Répondre librement » sticky toujours atteignable ; focus trap obligatoire ; sanitize DOMPurify de tout texte payload (NFR-003) ; locale FR avec lundi début de semaine ; double soumission impossible (FR-018) ; reduced motion neutralise GSAP (FR-017).
**Scale/Scope** : 11 wrappers (`ChatBottomSheet` orchestrateur + 10 wrappers tool) ; ~60 fichiers Vue/TS attendus (composants + composables + store + tests + génération zod) ; ~2 000 LOC y compris tests.

## Constitution Check

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Toute donnée factuelle introduite par cette feature pointe-t-elle vers une `Source` `verified` ? | ✅ pass — feature purement UI ; les sources viennent du backend (`show_summary_card` reçoit `source?` par champ et l'affiche en lecture seule). Le peg `655.957` est une constante backend sourcée (P5), pas dérivée frontend. |
| P2 | Multi-tenant RLS | Toute nouvelle table métier porte-t-elle `account_id` + RLS ? | ✅ pass — aucune nouvelle table. La feature consomme `/me/chat/threads/{id}/messages` (F14/F15) qui applique déjà la RLS via `app.current_account_id`. |
| P3 | Audit log append-only | Toute mutation introduite est-elle journalisée avec `source_of_change` ? | ✅ pass — toute soumission de sheet aboutit à un `INSERT` côté backend dans `chat_messages` ; l'audit (P3) est enregistré côté backend (F14/F15) avec `source_of_change=llm` ou `manual` selon le tool. Le frontend ne contourne pas le pipeline. |
| P4 | Versioning + snapshot candidatures | Les nouveaux référentiels/critères/formules portent-ils `version`/`valid_from`/`valid_to` ? | ✅ pass — non concerné, la feature ne crée pas de référentiel. |
| P5 | Money typé | Toute valeur monétaire utilise-t-elle `Money = {amount: Decimal, currency}` ? | ✅ pass — `ask_number` mode `money` envoie `{amount: string-decimal, currency: ISO 4217}`. La conversion live FCFA↔EUR utilise le peg fixe sourcé `655.957` (FR-009) ; aucune dérivation client de taux. USD/autres : valeur passée telle quelle au backend (post-MVP). |
| P6 | Pivot Indicateur unique | Les données ESG sont-elles stockées comme valeurs d'`Indicateur` ? | ✅ pass — non concerné côté UI ; le frontend n'écrit pas directement dans `Indicateur`. |
| P7 | Plateforme fermée aux intermédiaires | La feature évite-t-elle tout rôle Intermédiaire ? | ✅ pass — UI réservée au rôle PME (chat). Aucun nouveau rôle. |
| P8 | Édition manuelle + sync LLM | Tout champ alimenté par le LLM est-il modifiable manuellement ? La mutation manuelle invalide-t-elle le contexte LLM en temps réel ? | ✅ pass — Q1 a confirmé que la DB est source de vérité : aucune saisie partielle locale, reconstitution depuis le thread au reload. Les écrans d'édition manuelle (P8) sont hors scope F39 mais le contrat de reconstitution les respecte (un message tool soumis devient une donnée DB éditable ailleurs). |
| P9 | Tool-use LLM fiable | Nouveaux tools : nom verbal, "use when / don't use when", schéma Pydantic strict, eval gating ? | ✅ pass — F39 n'introduit aucun nouveau tool ; elle est l'UI consommatrice des tools définis par F15. La validation zod côté UI est dérivée des Pydantic backend (FR-014, génération `pnpm gen:tools`). |
| P10 | UX bottom sheet | Les composants interactifs vivent-ils dans le bottom sheet ? Bouton « Répondre librement » présent ? | ✅ pass — c'est la raison d'être de la feature. FR-001, FR-004, FR-005 garantissent la règle. |

**Verdict** : tous les gates ✅. Aucune violation. Pas de `Complexity Tracking` à remplir.

### Contraintes techniques (rappel)

- Stack Nuxt 4 + Vue 3.5 Composition API + Pinia + Tailwind v4 + GSAP 3.12, en place.
- Génération de schémas zod depuis OpenAPI backend via script `pnpm gen:tools` (à créer dans cette feature) — sortie dans `frontend/app/types/tools/`.
- Aucun bundle additionnel : `vue-virtual-scroller` est requis pour la virtualisation `ask_select` (200 pays). Si absent, ajouter en dépendance MVP.
- Hébergement production Europe / Afrique de l'Ouest (frontend statique CDN / SSR Nuxt) — conforme.

## Project Structure

### Documentation (this feature)

```text
specs/039-bottom-sheet-engine/
├── plan.md              # ce fichier
├── research.md          # Phase 0 (décisions techniques)
├── data-model.md        # Phase 1 (entités UI : ToolInstruction, ToolResponse, SheetState)
├── quickstart.md        # Phase 1 (parcours dev local)
├── contracts/
│   ├── orchestrator-events.md   # Événements émis/consommés par ChatBottomSheet
│   ├── tool-payloads.md         # Forme attendue de chaque payload (mirror Pydantic)
│   └── chat-message-submit.md   # Contrat d'écriture sortante vers /me/chat/threads/{id}/messages
└── tasks.md             # Phase 2 (à créer par /speckit-tasks)
```

### Source Code (repository root)

```text
frontend/
├── app/
│   ├── components/
│   │   └── chat/
│   │       └── bottom-sheet/
│   │           ├── ChatBottomSheet.vue         # orchestrateur racine
│   │           ├── BottomSheetShell.vue        # layout commun (header, sticky « Répondre librement », footer Valider)
│   │           ├── AskQcu.vue
│   │           ├── AskQcm.vue
│   │           ├── AskYesNo.vue
│   │           ├── AskSelect.vue
│   │           ├── AskNumber.vue
│   │           ├── AskDate.vue
│   │           ├── AskDateRange.vue
│   │           ├── AskRating.vue
│   │           ├── AskFileUpload.vue
│   │           ├── ShowForm.vue
│   │           ├── ShowSummaryCard.vue
│   │           └── __tests__/
│   │               ├── ChatBottomSheet.test.ts
│   │               ├── AskQcu.test.ts
│   │               ├── AskQcm.test.ts
│   │               ├── AskYesNo.test.ts
│   │               ├── AskSelect.test.ts
│   │               ├── AskNumber.test.ts
│   │               ├── AskDate.test.ts
│   │               ├── AskDateRange.test.ts
│   │               ├── AskRating.test.ts
│   │               ├── AskFileUpload.test.ts
│   │               ├── ShowForm.test.ts
│   │               └── ShowSummaryCard.test.ts
│   ├── composables/
│   │   ├── useChatBottomSheet.ts               # API publique : open(tool, payload, context), close, current
│   │   ├── useBottomSheetAnimation.ts          # GSAP slideUp/slideDown + reducedMotion
│   │   └── useBottomSheetSubmit.ts             # POST /me/chat/threads/{id}/messages + déduplication
│   ├── stores/
│   │   └── chatBottomSheet.ts                  # Pinia store éphémère { current: ToolInstruction | null, isClosing: boolean }
│   ├── types/
│   │   └── tools/                              # généré par `pnpm gen:tools`
│   │       ├── index.ts                        # union `ToolInstruction`, `ToolResponse`
│   │       ├── ask_qcu.ts
│   │       ├── ask_qcm.ts
│   │       ├── … (un fichier par tool)
│   │       └── show_summary_card.ts
│   └── utils/
│       ├── sanitize.ts                         # wrapper DOMPurify (texte ou HTML restreint)
│       └── moneyPeg.ts                         # constante 655.957 (importée du backend via /config public ou fallback)
└── scripts/
    └── gen-tools.mjs                           # génère types/tools/* depuis /openapi.json (FR-014)
```

**Structure Decision** : la feature s'intègre dans la structure existante `frontend/app/` (Nuxt 4) sans en créer de nouvelle. Tous les composants, composables et stores suivent les conventions déjà en place (`shell/`, `ui/`, `composables/`, `stores/`). Le sous-dossier `chat/bottom-sheet/` regroupe la totalité du moteur. Les types générés sont dans `app/types/tools/` pour rester importables sans alias supplémentaire. Le script de génération `scripts/gen-tools.mjs` est ajouté à `package.json` sous `gen:tools` et invoqué en pré-build CI.

## Complexity Tracking

Aucune violation des principes constitutionnels — section non remplie.
