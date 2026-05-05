# Implementation Plan: F51 — Matching offres + Wizard candidature + Simulateur (UI de F25/F26/F27)

**Branch**: `051-matching-candidatures-simulateur-ui` | **Date**: 2026-05-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/051-matching-candidatures-simulateur-ui/spec.md`

## Summary

F51 livre l'**UI conversationnelle et applicative** du parcours « trouver un financement vert » au-dessus des backends F25 (matching), F26 (générateur dossiers), F27 (simulateur), F34 (`/me/candidatures`) et F22 (documents) :

- **`/matching`** : sélecteur projet + liste cards triées par compat, filtres URL-persisted, drawer détail, comparateur (max 3, localStorage), carte Leaflet, redirection wizard.
- **`/candidatures`** : table candidatures, **wizard 5 étapes** avec autosave 800 ms (draft `snapshot_json`), checklist documents (F50), chat contextuel (F41), double confirmation soumission, timeline détail.
- **`/simulateur`** : 4 sliders + recalcul debounced 300 ms, charts (F40), historique sauvegardable, CTA pré-filtre vers `/matching`.

L'effort est **~70 % frontend** (Nuxt 4 + Pinia + Tailwind v4 + gsap + chart.js + Leaflet + driver.js + bottom sheet F39 + chat F41 + viz F40) et **~30 % backend** (extensions ciblées : detail+timeline candidatures, draft autosave + submit avec snapshot intangible, save+list simulations historique, endpoint `/me/offres` listing global avec filtre).

Aucun nouveau référentiel ; respect strict des invariants P1, P3, P4 (snapshot intangible candidatures), P5 (Money typé), P7 (pas de notification automatisée intermédiaire), P8 (sync EventBus chat ↔ wizard), P10 (toute saisie dans bottom sheet F39).

## Technical Context

**Language/Version** : Frontend TypeScript 5.6 + Vue 3.5 (Nuxt 4) ; Backend Python 3.12 (FastAPI).
**Primary Dependencies** :

- Frontend : Nuxt 4, Pinia, Tailwind v4, gsap (bottom sheet F39), `chart.js` + viz F40 (`<VizBarChart>`, `<VizLineChart>`, `<VizPieChart>`), `leaflet` + `@vue-leaflet/vue-leaflet`, `driver.js` (onboarding wizard step 1), chat F41 (`<ChatBottomSheet>`), `nuxt-security`, vitest + @vue/test-utils + Playwright.
- Backend : FastAPI, SQLAlchemy 2.x (existant), Alembic (migration mineure), Pydantic v2 (`extra='forbid'`), service `app/candidatures/service.py` étendu, `app/simulation/service.py` étendu.

**Storage** : PostgreSQL 16 (RLS via `app.current_account_id`). Aucune nouvelle table métier obligatoire ; deux extensions :

1. Colonnes ajoutées sur la table `candidature` existante (issue F26/F34) : `step_courant SMALLINT`, `progression_pct SMALLINT`, `draft_snapshot_json JSONB`, `submitted_at TIMESTAMPTZ`, `submitted_snapshot_json JSONB` immuable. Index partiel `(account_id, statut) WHERE statut='brouillon'`.
2. Nouvelle table `simulation_savee` `{id, account_id, label, projet_id NULL, offre_id NULL, hypotheses_json, results_json, created_at, deleted_at}` + RLS. Pas de `valid_from/valid_to` (ce n'est pas un référentiel — P4 N/A).
3. Optionnel : la table `offre` existe (catalogue F08) — F51 expose un endpoint `/me/offres` lecture filtrable agrégeant nom intermédiaire + géoloc.

**Testing** :

- Backend : `pytest --cov` (markers unit/integration), `httpx` TestClient. Coverage ≥ 80 % (`fail_under`).
- Frontend : `vitest run` (unit composants + stores + composables : autosave debounce, filtre URL, pré-fill simulateur→matching), Playwright (E2E parcours matching→wizard→soumission, simulateur→matching, comparateur 3 offres).

**Target Platform** : Frontend SPA SSR Nuxt 4 (port 3001) ; Backend FastAPI (port 8010). Production : Europe / Afrique de l'Ouest uniquement.

**Project Type** : web-service (backend FastAPI) + web-app (Nuxt 4) — voir CLAUDE.md.

**Performance Goals** :

- `/matching` LCP < 2 s sur catalogue 50 offres (SC-001).
- Simulateur recalcule + charts < 200 ms perçus (SC-003) — debounce 300 ms côté input, optimistic UI sur charts, pas de flicker.
- Wizard transition étape < 200 ms (gsap, FR-004 spec).
- Autosave debounce 800 ms (FR-008 spec).

**Constraints** :

- Toute saisie interactive du chat F41 dans bottom sheet F39 (P10) ; bouton « Répondre librement » présent.
- Soumission candidature = snapshot **immuable** (P4) reproductible 5 ans ; double confirmation (modale + checkbox).
- Comparateur stocké **localStorage** (pas multi-device au MVP — `Assumptions` spec).
- Devises : FCFA + EUR uniquement (P5, parité 655.957 figée). Pas d'USD MVP.
- Pas de notification push/webhook vers intermédiaire (P7) — statuts mis à jour manuellement par PME ou admin.

**Scale/Scope** :

- Catalogue : jusqu'à 50 offres dans le seed actuel (SC-001 cible). 200 offres restent linéaires (index `(secteur, type, montant_max)` existant).
- Wizard : 5 étapes, ~30 champs dont 8-10 documents typiques.
- Simulateur historique : cap 50 simulations/PME (purge soft post-MVP).

### Composants UI livrés

`pages/matching/index.vue`, `pages/matching/compare.vue`, `pages/candidatures/index.vue`, `pages/candidatures/[id].vue`, `pages/candidatures/new.vue` (wizard 5 étapes), `pages/simulateur/index.vue`, `pages/simulateur/historique.vue`,
`components/matching/{OffreCard,FiltresPanel,CompareTable,LeafletOffresMap,OffreDrawer,EmptyMatching}.vue`,
`components/candidatures/{CandidaturesTable,Wizard,WizardStepIndicator,StepOffreProjet,StepDataSnapshot,StepDocuments,StepReponsesLibres,StepRecap,DocumentsChecklist,SubmissionModal,CandidatureTimeline,DocumentsManquantsBanner}.vue`,
`components/simulateur/{SliderPanel,ResultsCharts,SaveSimulationSheet,HistoriqueList}.vue`,
`composables/{useMatchingFilters,useComparateur,useWizardAutosave,useWizardNavigation,useSimulateurDebounce}.ts`,
`stores/{matching,candidatures,simulateur}.ts`,
`services/api/{matching,candidatures,simulateur,offres}.ts`,
`types/{matching,candidatures,simulateur}.ts`.

## Constitution Check

*GATE: doit passer avant Phase 0. Re-évalué après Phase 1.*

Reference : [.specify/memory/constitution.md](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | F51 ne crée aucune assertion ESG/financière nouvelle ; chaque offre listée pointe vers la `Source` du catalogue F07/F08. Le simulateur étiquette ses sorties comme « estimations calculées » (FR-020 spec) avec lien vers la formule (référentiel F09). Aucun nouveau tool LLM. | ✅ |
| P2 | Multi-tenant RLS | `simulation_savee` porte `account_id NOT NULL` + RLS `tenant_isolation`. Les colonnes ajoutées à `candidature` héritent de la RLS existante de la table. Cross-tenant → 404 (404 normal pour `GET /me/candidatures/{id}`). | ✅ |
| P3 | Audit log append-only | Toutes les mutations (create candidature → déjà F25 ; autosave draft → `source_of_change='manual'` (1 audit par étape, pas 1 par frappe — voir research §2) ; submit → audit `manual` ; save simulation → `manual`) journalisées via `record_audit`. | ✅ |
| P4 | Versioning + snapshot candidatures | À la soumission, `submitted_snapshot_json` est figé (entreprise + projet + offre + skills version + valid_from + valid_to + payload réponses + documents joints), reproductible 5 ans. **Aucune modification autorisée après `submitted_at`** (DB constraint + service rejette). | ✅ |
| P5 | Money typé | Tous les montants UI (offre, simulateur, candidature) sérialisés `{amount: string Decimal, currency: 'XOF'\|'EUR'}`. Le frontend utilise un util `formatMoney(money, locale)` ; aucun calcul `Number` sur des montants. Le simulateur reçoit/renvoie des `Money`. | ✅ |
| P6 | Pivot Indicateur unique | Pas d'indicateur ESG nouveau. Les valeurs ESG du wizard (étape 4 réponses libres ou snapshot étape 2) renvoient à `Indicateur` existants (lecture seule). | ✅ |
| P7 | Plateforme fermée aux intermédiaires | Aucun rôle nouveau. Aucune notification push/webhook vers intermédiaire. La mise à jour de statut de candidature reste manuelle (PME ou admin existant F34). Pour partager une candidature acceptée, on passe par F30 attestation Ed25519 + QR — hors scope F51. | ✅ |
| P8 | Édition manuelle + sync LLM | Le wizard étape 4 utilise le chat F41 ; toute mutation manuelle d'un champ wizard émet `EventBus.emit('candidature:updated')` qui invalide le contexte chat (rechargement du tour suivant). Inversement, lorsqu'un tool chat met à jour un champ wizard, le store Pinia déclenche un re-render et l'autosave. | ✅ |
| P9 | Tool-use LLM fiable | F51 n'introduit aucun nouveau tool. Le chat F41 expose les tools déjà éval-gatés (cite_source, suggest_value). Si un tool `prefill_candidature_from_documents` est ajouté, il devra suivre P9 (eval ≥50, schéma strict, ≤10 tools concurrents). Hors scope MVP. | ✅ (deferred) |
| P10 | UX bottom sheet | Toutes les saisies interactives initiées depuis le chat (étape 4 wizard) sont dans un bottom sheet F39. Le drawer offre, la modale soumission, les sliders simulateur restent **applicatifs** (pas issus du chat) — ils peuvent rester inline ; le chat F41 force le bottom sheet pour ses propres prompts. Bouton « Répondre librement » présent dans tous les bottom sheets chat. | ✅ |

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ; LLM via OpenRouter ; embeddings Voyage `voyage-3.5` (1024 dim) — non utilisé en F51 MVP.
- Dev local : backend en `.venv`, Postgres seul service Docker, frontend `pnpm dev`.
- Hébergement production : Europe ou Afrique de l'Ouest uniquement.
- Conformité : RGPD + UEMOA 20/2010 + loi ivoirienne 2013-450. Snapshot candidature reproductible 5 ans.
- Langue : français par défaut. Anglais activé uniquement si l'`offre.accepted_languages` inclut `'en'`.

**Aucune violation constitutionnelle.** Une seule entrée dans Complexity Tracking : ajout du champ `draft_snapshot_json` séparé du `submitted_snapshot_json` (deux colonnes JSONB sur la même table).

## Project Structure

### Documentation (this feature)

```text
specs/051-matching-candidatures-simulateur-ui/
├── plan.md              # ce fichier
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── matching_api_extensions.md
│   ├── candidatures_api_extensions.md
│   ├── simulateur_api_extensions.md
│   └── ui_contracts.md
├── checklists/
│   └── requirements.md
├── spec.md
└── tasks.md             # généré par /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── matching/
│   │   ├── router.py                          # extension : GET /me/offres (catalogue filtrable global)
│   │   ├── service.py                         # extension : list_offres_for_account (filtre type/secteur/durée/montant)
│   │   └── schemas.py                         # extension : OffreFilters, OffreListItem
│   ├── candidatures/
│   │   ├── router.py                          # extension : GET /me/candidatures/{id}, PATCH wizard draft, POST submit
│   │   ├── service.py                         # extension : get_detail, save_draft, submit_with_snapshot, list_timeline
│   │   └── schemas.py                         # extension : CandidatureDetail, WizardDraftIn, WizardSubmitIn, TimelineEvent
│   ├── simulation/
│   │   ├── router.py                          # extension : GET /me/simulations, POST /me/simulations/{id}/save, DELETE /me/simulations/{id}
│   │   ├── service.py                         # extension : save, list, soft_delete
│   │   └── schemas.py                         # extension : SimulationSaveIn, SimulationListItem
│   └── audit/
│       └── recorder.py                        # réutilisé tel quel (pas de modification)
└── alembic/versions/
    └── 0051_candidatures_wizard_simulateur_savee.py   # NOUVELLE migration : colonnes candidature + table simulation_savee + index

frontend/
├── app/
│   ├── pages/
│   │   ├── matching/
│   │   │   ├── index.vue                      # NOUVEAU
│   │   │   └── compare.vue                    # NOUVEAU
│   │   ├── candidatures/
│   │   │   ├── index.vue                      # NOUVEAU
│   │   │   ├── [id].vue                       # NOUVEAU
│   │   │   └── new.vue                        # NOUVEAU (wizard 5 étapes)
│   │   └── simulateur/
│   │       ├── index.vue                      # NOUVEAU
│   │       └── historique.vue                 # NOUVEAU
│   ├── components/
│   │   ├── matching/
│   │   │   ├── OffreCard.vue
│   │   │   ├── FiltresPanel.vue
│   │   │   ├── CompareTable.vue
│   │   │   ├── LeafletOffresMap.vue           # chunk async
│   │   │   ├── OffreDrawer.vue
│   │   │   └── EmptyMatching.vue
│   │   ├── candidatures/
│   │   │   ├── CandidaturesTable.vue
│   │   │   ├── Wizard.vue                     # parent + transitions gsap
│   │   │   ├── WizardStepIndicator.vue
│   │   │   ├── StepOffreProjet.vue            # étape 1
│   │   │   ├── StepDataSnapshot.vue           # étape 2 (read-only + lien profil)
│   │   │   ├── StepDocuments.vue              # étape 3 (checklist + upload F50 embed)
│   │   │   ├── StepReponsesLibres.vue         # étape 4 (chat F41 + bottom sheet)
│   │   │   ├── StepRecap.vue                  # étape 5
│   │   │   ├── DocumentsChecklist.vue
│   │   │   ├── SubmissionModal.vue            # double confirmation
│   │   │   ├── CandidatureTimeline.vue
│   │   │   └── DocumentsManquantsBanner.vue
│   │   └── simulateur/
│   │       ├── SliderPanel.vue
│   │       ├── ResultsCharts.vue              # 3 charts F40
│   │       ├── SaveSimulationSheet.vue        # bottom sheet F39
│   │       └── HistoriqueList.vue
│   ├── composables/
│   │   ├── useMatchingFilters.ts              # filtres URL-persisted
│   │   ├── useComparateur.ts                  # localStorage max 3
│   │   ├── useWizardAutosave.ts               # debounce 800 ms + buffer offline
│   │   ├── useWizardNavigation.ts             # validation par étape + transitions gsap
│   │   └── useSimulateurDebounce.ts           # debounce 300 ms input → API
│   ├── stores/
│   │   ├── matching.ts
│   │   ├── candidatures.ts
│   │   └── simulateur.ts
│   ├── services/api/
│   │   ├── matching.ts
│   │   ├── candidatures.ts
│   │   ├── simulateur.ts
│   │   └── offres.ts
│   └── types/
│       ├── matching.ts
│       ├── candidatures.ts
│       └── simulateur.ts
└── tests/
    ├── unit/
    │   ├── matching/{OffreCard,FiltresPanel,CompareTable,useMatchingFilters,useComparateur}.test.ts
    │   ├── candidatures/{Wizard,StepDocuments,SubmissionModal,useWizardAutosave}.test.ts
    │   └── simulateur/{SliderPanel,ResultsCharts,useSimulateurDebounce}.test.ts
    └── e2e/
        ├── matching-flow.spec.ts              # US1, US2, US5 + carte
        ├── matching-compare.spec.ts           # comparateur 3 offres
        ├── candidatures-wizard.spec.ts        # US7 wizard complet + autosave reload
        ├── candidatures-submission.spec.ts    # double confirmation + snapshot intangible
        ├── candidatures-timeline.spec.ts      # détail + statut
        ├── simulateur-flow.spec.ts            # sliders + charts + historique
        └── simulateur-to-matching.spec.ts     # CTA pré-filtrage

backend/tests/
├── unit/
│   ├── candidatures/
│   │   ├── test_save_draft.py
│   │   ├── test_submit_snapshot.py            # snapshot intangible figé
│   │   └── test_get_detail.py
│   ├── simulation/
│   │   └── test_save_list.py
│   └── matching/
│       └── test_list_offres_filters.py
└── integration/
    ├── test_candidatures_wizard_api.py
    ├── test_simulateur_history_api.py
    └── test_offres_listing_api.py
```

**Structure Decision** : web-service (backend) + web-app (frontend) conforme à CLAUDE.md. Aucune nouvelle racine. F51 étend les domaines existants `matching/`, `candidatures/`, `simulation/` côté backend ; côté frontend, création de trois domaines de pages `matching/`, `candidatures/`, `simulateur/` et de leurs composants associés.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Deux colonnes JSONB séparées sur `candidature` (`draft_snapshot_json` ET `submitted_snapshot_json`) | P4 exige un snapshot **immuable** à la soumission. Un seul JSONB avec flag `is_submitted` autoriserait une mutation post-soumission (faille audit). Avoir deux colonnes garantit une contrainte simple : `submitted_snapshot_json` est NULL avant soumission, NOT NULL et figé après ; `draft_snapshot_json` peut rester pour audit/reprise mais n'a aucune valeur juridique. | Une seule colonne forcerait une logique applicative (et non DB) pour interdire la modification, augmentant le risque de violation P4 sur 5 ans. Les deux colonnes coûtent ~négligeable en stockage (JSONB compressé), mais sécurisent l'invariant constitutionnel. |

## Phase 0 — Research (résolu dans `research.md`)

Voir [research.md](./research.md) pour les décisions techniques détaillées :

1. **Sélecteur projet pour `/matching`** — l'endpoint `/me/projets/{projet_id}/matching` exige un projet ; décision : la page `/matching` lit le projet « actif » dans `useUserStore` (déjà disponible F43) ; si aucun projet, empty state avec CTA « Créer un projet ». Alternative globale `/me/offres` exposée pour la liste catalogue **non scorée** (CTA « Voir toutes les offres »).
2. **Audit autosave** — chaque sauvegarde de draft génère un audit `manual` ; pour éviter le bruit, on ne journalise **qu'au passage d'étape** (pas à chaque keystroke). L'autosave inter-étape met à jour la colonne sans audit ; le passage d'étape (PATCH explicite) déclenche l'audit.
3. **Filtres URL-persisted** — `useRoute().query` synchronisé bidirectionnellement avec le store via `watch`/`navigateTo({ query, replace: true })`. Ouverture partage = état restauré.
4. **Comparateur localStorage** — clé `mefali:matching:comparator` (objets `{offre_id, projet_id, label, montant, devise}`). Cap 3 strict. Reset cross-projet (changement de projet = vidage).
5. **Carte Leaflet** — chunk async `() => import('leaflet')` ; tile OpenStreetMap public ; pins clusterisés via `leaflet.markercluster` (déjà connue) ; empty state si aucune `geolocation` côté intermédiaire.
6. **Wizard transitions gsap** — `gsap.timeline()` 200 ms (ease `power2.out`), respect `prefers-reduced-motion` (transitions instantanées si flag).
7. **Autosave robuste hors-ligne** — `useWizardAutosave` bufferise localStorage en cas d'échec réseau, indicateur « sauvegarde en attente » visible, sync au retour réseau (`navigator.onLine`).
8. **Snapshot intangible** — service backend `submit_with_snapshot` construit un dict JSON figé `{entreprise, projet, offre, skills_version, indicateurs_valid_from_to, draft_payload, documents}` puis insère dans `submitted_snapshot_json` avec contrainte `WHERE submitted_at IS NULL` (idempotence + atomicité).
9. **Debounce simulateur** — utilitaire `useSimulateurDebounce(300)` annule les requêtes en vol via `AbortController` ; les charts gardent le dernier résultat valide pendant le calcul (pas de flash blanc).
10. **Charts F40** — `<VizBarChart>`, `<VizLineChart>`, `<VizPieChart>` reçoivent un `data` reactive ; les transitions internes chart.js gèrent l'animation fluide.
11. **Comparateur 3 offres en table** — composant `<CompareTable>` Tailwind v4 avec sticky col label gauche, mode mobile = stack (cartes empilées avec scroll horizontal de la colonne data).
12. **Devises et formatage** — util `formatMoney({amount, currency}, locale='fr-FR')` avec `Intl.NumberFormat` ; conversion FCFA↔EUR via parité figée 655.957 (sourcée P5).

## Phase 1 — Design & Contracts (résolu)

- **`data-model.md`** — schéma des nouvelles colonnes `candidature.{step_courant, progression_pct, draft_snapshot_json, submitted_at, submitted_snapshot_json}`, table `simulation_savee`, transitions de statut candidature, RLS, index, triggers (interdiction de mutation après `submitted_at`).
- **`contracts/matching_api_extensions.md`** — `GET /me/offres?type=&montant_min=&montant_max=&duree=&intermediaire_id=&secteur=&limit=&cursor=` (catalogue paginé) + détails de `/me/projets/{projet_id}/matching` déjà F25.
- **`contracts/candidatures_api_extensions.md`** — `GET /me/candidatures/{id}` (detail+timeline), `PATCH /me/candidatures/{id}/draft` (autosave + step), `POST /me/candidatures/{id}/submit` (snapshot intangible + double confirm côté serveur via flag `confirmed=true` body), `GET /me/candidatures/{id}/timeline`.
- **`contracts/simulateur_api_extensions.md`** — `GET /me/simulations` (liste historique paginée), `POST /me/simulations/{id}/save` (sauvegarde nommée d'une simulation calculée), `DELETE /me/simulations/{id}` (soft-delete).
- **`contracts/ui_contracts.md`** — props/events des composants F51, modèle Pinia (`stores/matching.ts`, `stores/candidatures.ts`, `stores/simulateur.ts`), événements EventBus avec le chat F41 (`candidature:updated`, `wizard:step:changed`, `simulateur:saved`).
- **`quickstart.md`** — comment lancer F51 en dev (migration 0051, seed catalogue offres, premier match, premier wizard, première simulation, comparateur).

CLAUDE.md mis à jour pour pointer vers `specs/051-matching-candidatures-simulateur-ui/plan.md` (entre marqueurs SPECKIT).
