# Implementation Plan: Profil Entreprise & Projets — UI (F43)

**Branch**: `043-profile-entreprise-projets-ui` | **Date**: 2026-05-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/043-profile-entreprise-projets-ui/spec.md`

## Summary

Brancher l'UI Nuxt 4 (pages `/profil/entreprise`, `/profil/projets`, `/profil/projets/[id]`) sur les services backend déjà livrés par F11 (`app/entreprise/`, exposé via `/me/entreprise`, `/me/entreprise/completeness`, `/me/entreprise/events`) et F12-profile (`app/projets/`, exposé via `/me/projets`, `/me/projets/{id}`, `/me/projets/events`, `/me/projets/{id}/documents`). La feature est **strictement frontend** côté écriture de code applicatif : aucun nouvel endpoint, aucune nouvelle table, aucune migration. Elle ajoute :

- 3 pages Nuxt + une famille de composants `components/profil/*` (sections lecture/édition, wizard projet 4 étapes, dialogue conflit, drawer historique).
- 1 store Pinia projets (`stores/projets.ts`) + extension du store `entreprise.ts` (passer de simple « completion » à un agrégat `data + version + completion`).
- 1 composable `useEntrepriseProfile` (autosave debounced 800 ms avec `AbortController`, mapping des erreurs 409 → dialogue conflit) et 1 composable `useProjet` (équivalent pour un projet précis).
- Branchement EventBus chat ↔ profil : réutilisation de `useChatEventBus` existant ; les SSE backend `/me/entreprise/events` et `/me/projets/events` ne sont **pas** consommés en MVP UI (le backend les expose mais le wiring complet relèvera d'une feature post-MVP) — la sync chat → UI passe par l'`EventBus` front, déclenché à la réception d'un tool result mutation depuis `useChatToolBridge`.
- Une couche de mapping de **labels affichés** pour les statuts projet : la clarification spec retient `brouillon, actif, en_candidature, finance, cloture, abandonne`, mais le backend (déjà déployé en F12-profile) gèle 5 statuts canoniques `brouillon, en_recherche_financement, finance, en_execution, cloture`. Le plan **aligne le spec sur le backend** côté valeurs persistées (les 5 statuts canoniques restent la source de vérité) et n'ajoute qu'un mapping de libellés FR au niveau UI. Cette décision est consignée en `research.md` et reflétée par une mise à jour des FR-011 et de la liste « statut » dans le data-model.

## Technical Context

**Language/Version**: TypeScript 5.x + Vue 3 / Nuxt 4 (frontend) ; Python 3.12 (backend, **lecture seule** — aucun changement applicatif prévu).
**Primary Dependencies**:
- Frontend (déjà installés en F36–F42) : Nuxt 4, Pinia, Tailwind v4, gsap (transitions wizard et bottom-sheet), `decimal.js` ou équivalent (à confirmer en research — `Number.toFixed` est insuffisant pour P5), driver.js (non requis ici), composables existants `useChatEventBus`, `useMoneyFormat`, `useToast`, `useFieldId`, `useReducedMotion`.
- Backend : aucune nouvelle dépendance.
**Storage**: PostgreSQL 16 + pgvector (déjà). Tables consommées : `entreprises`, `projets`, `documents_projet`, `documents_entreprise`, `audit_log`. Aucune nouvelle table.
**Testing**:
- Frontend : vitest pour les composables `useEntrepriseProfile`, `useProjet`, `useProjetWizard` (validation par étape) et le store `projets` ; `@vue/test-utils` pour les pages clés ; tests de composants `SectionEditor.vue`, `ProjetWizard.vue`, `ConflictDialog.vue`, `MoneyField.vue`, `CountryMultiSelect.vue`.
- E2E : Playwright (`frontend/tests/e2e/`) — parcours complet (autosave + reload, wizard projet, suppression, sync chat ↔ profil simulée via mock). Réutilise la base configurée en F38.
- Backend : aucun nouveau test — la couverture F11/F12-profile reste valide.
**Target Platform**: Web responsive — desktop ≥ 1280 px (lecture deux colonnes possible), tablette 768–1279 px (mono-colonne), mobile < 768 px (sections empilées, wizard plein écran).
**Project Type**: Web application (Nuxt 4 frontend + FastAPI backend).
**Performance Goals**:
- `/profil/entreprise` premier rendu utile (sections affichées avec données) < 1 s sur connexion 4G typique (SC-001).
- Mutation chat → reflet UI < 2 s p95 (SC-003).
- Autosave : `PATCH /me/entreprise` < 1 s p95 sur réseau correct.
- Wizard projet : transition étape ↔ étape ≤ 200 ms (gsap).
**Constraints**:
- **P5 Money typé** : montants stockés et calculés en Decimal côté front (jamais `Number`) ; conversion d'affichage XOF↔EUR avec peg fixe `655.957` (sourcé), USD via taux du jour exposé par le backend.
- **P8 Sync bidirectionnelle** : toute mutation manuelle invalide le contexte LLM ; toute mutation chat est propagée à l'UI ouverte. Ici, l'invalidation est gérée backend-side (déjà câblée via `entreprise/events.py` et `projets/events.py`) ; le front se contente d'écouter l'`EventBus` chat et de déclencher un re-fetch de la section concernée.
- **Concurrence optimiste** : tout `PATCH` envoie le `version` courant ; un 409 retourne `ConflictOut { current_version, your_version }` → le front ouvre `ConflictDialog` (FR-020).
- **a11y WCAG 2.1 AA** : tab order strict, erreurs annoncées via `aria-describedby`, focus trap dans modale wizard et conflit.
- Hébergement Europe / Afrique de l'Ouest (constitution).
**Scale/Scope**: 3 pages (entreprise, liste projets, détail projet) + ~12 composants nouveaux + 2 stores + 3 composables. ~600–900 LOC frontend nouvelles. Volume utilisateur : MVP — quelques centaines de PME pendant la phase pilote, ~1–5 projets par PME (le MVP pose la limite à un projet « principal », la liste est conservée pour cohabitation avec une future levée de la limite).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Pas de donnée factuelle ESG introduite par l'UI ; les valeurs affichées proviennent de F11/F12 où `source_id` est déjà imposé pour les seuils/indicateurs. La couche UI ne fabrique aucun chiffre. | ✅ N/A |
| P2 | Multi-tenant RLS | Toutes les ressources consommées (`/me/entreprise`, `/me/projets`) passent par les routes existantes qui appliquent déjà RLS via `account_id`. Le front ne fabrique aucune requête SQL. | ✅ |
| P3 | Audit log append-only | Toute mutation (`PATCH /me/entreprise`, `POST/PATCH/DELETE /me/projets`, upload/suppression de document) écrit déjà dans `audit_log` côté backend avec `source_of_change='manual'`. La feature s'appuie sur ce comportement existant. | ✅ |
| P4 | Versioning + snapshot candidatures | Pas de candidature soumise ni de référentiel modifié ici. La concurrence optimiste s'appuie sur le champ `version` existant côté F11/F12 (différent de la versioning constitutionnelle des référentiels, mais aligné dans la philosophie P4 de non-écrasement). | ✅ |
| P5 | Money typé | `MoneyField.vue` impose `{ amount: Decimal, currency: ISO 4217 }` ; aucune arithmétique `Number`. Le peg XOF↔EUR `655.957` est sourcé via une `Source verified` déjà persistée (cf. seed F03/P5). USD via taux backend. | ✅ |
| P6 | Pivot Indicateur unique | Aucune donnée ESG n'est saisie dans cette feature ; les indicateurs sont gérés en F11 (entreprise) déjà déployé. | ✅ N/A |
| P7 | Plateforme fermée aux intermédiaires | Aucune route, aucun rôle nouveau. Suppression projet = soft delete propriétaire seulement. | ✅ |
| P8 | Édition manuelle + sync LLM | C'est précisément l'objet de FR-018 à FR-021. La modification manuelle déclenche immédiatement un `PATCH` (qui invalide côté backend le contexte LLM via `entreprise/events.py`) ; la mutation chat est propagée via `useChatEventBus` → re-fetch local. La DB reste source de vérité. | ✅ |
| P9 | Tool-use LLM fiable | Aucun nouveau tool LLM dans cette feature (les tools `update_entreprise`, `update_projet`, `create_projet` existent déjà côté F17 et déclenchent les events backend que cette UI consomme). | ✅ N/A |
| P10 | UX bottom sheet | La feature est **hors flux chat** : pas de bulle LLM. Le wizard projet est une modale plein écran (justifié : usage hors chat, pas une réponse à une question LLM). Aucun input n'est rendu inline dans une bulle LLM puisque la feature ne touche pas à la timeline chat. | ✅ |

Aucun gate ❌. Pas de Complexity Tracking nécessaire.

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ✓ (existant inchangé).
- Dev local : backend `.venv`, Postgres seul service Docker, frontend `pnpm dev` ✓.
- Hébergement production : Europe ou Afrique de l'Ouest uniquement ✓.
- Conformité : RGPD + loi ivoirienne 2013-450 + UEMOA 20/2010 — la feature n'introduit aucun nouveau traitement personnel ; lecture/écriture sur des champs déjà déclarés au registre.
- Langue : français par défaut ✓ ; chaînes UI ajoutées dans `frontend/app/locales/fr.ts` (existant depuis F42) via `useT()`.

## Project Structure

### Documentation (this feature)

```text
specs/043-profile-entreprise-projets-ui/
├── plan.md              # Ce fichier
├── research.md          # Phase 0 — décisions techniques (Decimal lib, statuts mapping, conflict UX, EventBus wiring)
├── data-model.md        # Phase 1 — entités consommées (Entreprise, Projet, DocumentProjet) côté UI + ViewModel
├── quickstart.md        # Phase 1 — comment tester localement de bout en bout
├── contracts/
│   ├── frontend-api-consumption.md   # Contrats des endpoints consommés (entrées/sorties UI)
│   ├── frontend-components.md        # Contrats des composants/composables nouveaux
│   └── chat-eventbus-sync.md         # Contrat d'évènements UI ↔ chat (entity_updated, etc.)
├── checklists/
│   └── requirements.md               # Spec quality checklist (déjà créée)
└── tasks.md             # Phase 2 — généré par /speckit-tasks (PAS par /speckit-plan)
```

### Source Code (repository root)

```text
backend/                                    # AUCUNE MODIFICATION dans cette feature.
└── app/
    ├── entreprise/                         # F11 — déjà déployé
    │   ├── service.py                      # GET/PATCH /me/entreprise (utilisé)
    │   ├── completeness.py                 # /me/entreprise/completeness (utilisé)
    │   ├── events.py                       # SSE /me/entreprise/events (non consommé en MVP UI)
    │   └── documents_service.py            # /me/entreprise/documents (utilisé en P2 — pas P1)
    └── projets/                            # F12-profile — déjà déployé
        ├── service.py                      # GET/POST/PATCH/DELETE /me/projets (utilisé)
        ├── documents_service.py            # /me/projets/{id}/documents (utilisé pour US5)
        └── events.py                       # SSE /me/projets/events (non consommé en MVP UI)

frontend/
├── app/
│   ├── pages/
│   │   ├── profil/
│   │   │   ├── entreprise.vue              # NEW — page /profil/entreprise
│   │   │   └── projets/
│   │   │       ├── index.vue               # MODIFIE — page /profil/projets (existe en draft, à enrichir)
│   │   │       └── [id].vue                # NEW — page /profil/projets/{id}
│   │   └── projets/                        # legacy redirect ou suppression — à arbitrer en research
│   ├── components/
│   │   ├── profil/                         # NEW — famille profil
│   │   │   ├── EntrepriseHeader.vue        # barre complétion + actions globales
│   │   │   ├── SectionCard.vue             # carte de section (lecture/édition)
│   │   │   ├── SectionEditor.vue           # formulaire édition + autosave
│   │   │   ├── MoneyField.vue              # composant Money (Decimal + currency selector)
│   │   │   ├── CountryMultiSelect.vue      # ISO2 + cluster UEMOA en tête
│   │   │   ├── ProjetCard.vue              # carte liste projets
│   │   │   ├── ProjetEmptyState.vue        # état vide projets
│   │   │   ├── ProjetWizard.vue            # wizard modal 4 étapes
│   │   │   ├── ProjetWizardStep1.vue
│   │   │   ├── ProjetWizardStep2.vue
│   │   │   ├── ProjetWizardStep3.vue
│   │   │   ├── ProjetWizardStep4.vue
│   │   │   ├── ConflictDialog.vue          # dialogue résolution conflit (3 choix)
│   │   │   ├── HistoryDrawer.vue           # panneau latéral audit
│   │   │   └── ProjetDocuments.vue         # liste/upload documents projet
│   │   └── ui/                             # primitives existantes (UiFormField, UiInput, UiNumber, UiMultiSelect, UiModal, UiButton, UiSkeleton, UiToast, UiEmptyState, UiProgress, UiCard, UiBadge — déjà fournies par F37)
│   ├── composables/
│   │   ├── useEntrepriseProfile.ts         # NEW — autosave debounced + version + conflict
│   │   ├── useProjet.ts                    # NEW — idem pour un projet
│   │   ├── useProjetWizard.ts              # NEW — état + validation par étape
│   │   ├── useDecimal.ts                   # NEW — wrapper Decimal (decimal.js) + helpers
│   │   └── useChatEventBus.ts              # EXISTANT — utilisé pour entity_updated
│   ├── stores/
│   │   ├── entreprise.ts                   # MODIFIE — étend l'agrégat (data + version + completion)
│   │   └── projets.ts                      # NEW — liste + détail + version
│   ├── locales/
│   │   └── fr.ts                           # MODIFIE — ajout des clés profil/projets
│   └── assets/css/main.css                 # MODIFIE marginal — classes utilitaires si besoin
└── tests/
    ├── unit/
    │   └── composables/
    │       ├── useEntrepriseProfile.test.ts
    │       ├── useProjet.test.ts
    │       ├── useProjetWizard.test.ts
    │       └── useDecimal.test.ts
    ├── components/
    │   └── profil/
    │       ├── MoneyField.test.ts
    │       ├── CountryMultiSelect.test.ts
    │       ├── ConflictDialog.test.ts
    │       ├── ProjetCard.test.ts
    │       └── ProjetWizard.test.ts
    └── e2e/
        ├── profil-entreprise-autosave.spec.ts
        ├── profil-entreprise-completeness.spec.ts
        ├── profil-projets-wizard.spec.ts
        ├── profil-projets-delete-restore.spec.ts
        └── profil-conflict-chat-sync.spec.ts
```

**Structure Decision**: Application web mono-repo Nuxt 4 + FastAPI déjà en place ; cette feature ne touche que `frontend/app/`. Le découpage `components/profil/*` reflète la frontière de domaine UI (pages profil) sans empiéter sur `components/chat/*` (timeline LLM) ni sur `components/ui/*` (primitives génériques). Les tests sont déjà structurés en `unit/`, `components/`, `e2e/` (héritage F38/F42).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Aucune violation. Tableau vide.
