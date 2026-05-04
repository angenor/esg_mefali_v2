# Implementation Plan: Empreinte carbone UI (F47)

**Branch**: `047-empreinte-carbone-ui` | **Date**: 2026-05-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/047-empreinte-carbone-ui/spec.md`

## Summary

Livrer la page **`/carbone`** : UI dédiée au calcul, à la visualisation et au pilotage de l'empreinte carbone d'une PME (Scopes 1/2/3, drilldown par poste, courbe d'évolution, recalcul à la demande, wizard onboarding), branchée sur le backend **F28** déjà déployé (`POST /me/carbon/compute`, `GET /me/carbon/{year}`, `GET /me/carbon/{year}/reduction-plan`).

La feature est très majoritairement **frontend** mais nécessite **trois ajouts backend ciblés** pour rendre l'UI opérante :

1. `GET /me/carbon` — index multi-année des empreintes (pour US1 delta vs N-1, US4 courbe annuelle, US6 détection empty-state).
2. `POST /me/carbon/{year}/recompute` — replay du compute avec le `source_data_json` du dernier calcul de l'année + relookup des facteurs courants (US5 recalcul global manuel).
3. `POST /me/carbon/{year}/edit-line` — mutation ciblée d'une ligne (`code`, `quantity`, `country?`, `source_id`) qui reconstruit le `source_data` depuis le dernier calcul, applique la modification et persiste une nouvelle empreinte (US3 édition d'une donnée d'activité).

À ces ajouts s'attache une **extension non rétro-incompatible** du schéma `CarbonSourceItem` : ajout d'un champ optionnel `source_id: UUID | None` (NULL accepté côté `POST /me/carbon/compute` historique pour rétrocompat ; **obligatoire côté `POST .../edit-line`** — vérifié par contrat). Ce champ est propagé dans la `breakdown` afin que chaque ligne affichée par l'UI expose son justificatif (P1 Sourcing).

Aucune nouvelle table, aucune migration. Les tests backend ajoutés couvrent uniquement les trois nouveaux endpoints (5–6 cas chacun) et l'extension de schéma.

La feature ajoute :

- 1 page Nuxt : `pages/carbone/index.vue` (vue synthèse + drilldown + édition + recalcul + wizard empty-state ; année implicite = année courante avec sélecteur année à droite).
- 1 famille de composants `components/carbone/*` :
  - **Synthèse** : `CarbonOverview.vue` (KPI total + delta N-1 + couverture %), `ScopeDonut.vue` (répartition Scope 1/2/3), `EvolutionLineChart.vue` (courbe N vs N-1 ou multi-année).
  - **Détail** : `ScopeAccordion.vue` (un par scope, contient une liste de `EmissionLine.vue`), `EmissionLine.vue` (valeur + unité + facteur + pin source), `FactorSourcePopover.vue` (popover détail facteur version + valid_from + lien `<VizSourcePin>`).
  - **Actions** : `RecalcStrip.vue` (bouton "Recalculer" + horodatage "Dernier calcul" + spinner), `EditLineDrawer.vue` (orchestre l'ouverture du bottom sheet `ask_form` quantité+unité+source).
  - **States** : `LowCoverageBanner.vue` (avertissement < 60 %), `EmptyStateWizard.vue` (déclenche le wizard 3 étapes énergie→déplacements→achats via `ChatBottomSheet show_form`).
  - **P2** : `FactorReferentielSwitch.vue` (badge "Estimation" + switch ADEME/IPCC, désactivé au MVP avec infobulle "À venir"), `ExportPdfButton.vue` (P2, dépend F51).
- 1 store Pinia `useCarbonStore` (par année : footprint courant, index multi-année, breakdown groupé par scope, coverage %, état de chargement, dernier `computed_at`, mode wizard).
- 4 composables :
  - `useCarbon` (orchestre fetch index + footprint année courante + abonnement EventBus `entity_updated{carbon_footprint}`).
  - `useCarbonHistory` (fetch et mémorise l'index multi-année, dérive la série N vs N-1 pour `EvolutionLineChart`).
  - `useCarbonEdit` (orchestre l'ouverture du bottom sheet `ask_form` pour une ligne, soumet `POST .../edit-line`, met à jour le store post-réponse, émet `entity_updated`).
  - `useCarbonWizard` (gère les 3 étapes empty-state énergie/déplacements/achats avec persistance des réponses partielles dans `localStorage`, soumet en bloc `POST /me/carbon/compute` à la fin).
- 2 helpers purs :
  - `lib/groupCarbonByScope.ts` : transforme la `breakdown` plate en arborescence `Scope (1|2|3) → poste (combustion_fixe, electricite, achats, …) → ligne[]`. Les postes attendus pour le MVP sont déclarés dans une constante (`CARBON_EXPECTED_POSTS_BY_SCOPE`) — utile pour calculer la couverture % (postes renseignés ÷ postes attendus).
  - `lib/computeCarbonCoverage.ts` : à partir de la breakdown et de `CARBON_EXPECTED_POSTS_BY_SCOPE`, retourne `{ scope1: %, scope2: %, scope3: %, global: % }`.
- Réutilisation **maximale** des primitives F36/F37/F39/F40 : `<UiCard>`, `<UiBadge>`, `<UiButton>`, `<UiSkeleton>`, `<UiEmptyState>`, `<UiPopover>` (pour le détail facteur), `<UiBanner>` (avertissement couverture), `<ChatBottomSheet>` + `<ShowForm>` (pour `ask_form` ligne et wizard 3 étapes), `<VizDonutChart>`, `<VizLineChart>`, `<VizSourcePin>`. Aucune nouvelle bibliothèque graphique (chart.js déjà en place).
- Branchement EventBus chat ↔ carbone : à la réception d'`entity_updated{carbon_footprint}`, invalidation **ciblée** du footprint de l'année courante et de l'index multi-année. Inversement, toute modification locale (édition d'une ligne, recalcul global, fin de wizard) émet l'event correspondant pour propager aux autres surfaces (chat, dashboard F44 carte carbone si présente).

La page **réutilise** les patterns de F46 (`/scoring`) — store par tenant + composables fetch/edit/history + bottom sheet pour toute saisie + EventBus — pour préserver la cohérence d'expérience.

Côté backend, les trois ajouts sont **append-only en lecture/écriture** (`POST .../edit-line` et `POST .../recompute` insèrent une nouvelle ligne `carbon_footprint`, jamais de UPDATE/DELETE), RLS-aware (filtre `account_id`), audit-loggés (`source_of_change = manual` pour edit-line, `source_of_change = manual` pour recompute déclenché par la PME) et accompagnés de tests `pytest` (unit + integration).

## Technical Context

**Language/Version** : TypeScript 5.x + Vue 3 / Nuxt 4 (frontend) ; Python 3.12 (backend, **trois nouveaux endpoints + une extension de schéma**).

**Primary Dependencies** :

- Frontend (déjà installés en F36–F46) : Nuxt 4, Pinia, Tailwind v4, gsap (animations donut/drawer/wizard transitions), `chart.js` (donut + line via `viz/`), `decimal.js` (P5 — kgCO2e/tCO2e exposés en `Decimal` pour conserver la précision). Composables existants `useChatEventBus`, `useChatBottomSheet`, `useToast`, `useReducedMotion`, `useT`, `useAuth`, `useSourceFetch`, `useDecimal`, `useChartTheme`. Pattern Pinia identique à `useScoringStore` (F46).
- Backend : aucune nouvelle dépendance Python ; on s'appuie sur SQLAlchemy + Pydantic v2 déjà présents et sur `app.audit.record_audit` + `app.catalog.facteurs_emission.lookup.get_facteur` déjà utilisés par `app.carbon.service`.

**Storage** : PostgreSQL 16 + pgvector (déjà). Tables consommées en lecture : `carbon_footprint` (append-only, F28), `facteur_emission` (catalogue versionné F09), `source` (catalogue F09) pour le détail des factures/justificatifs liés à `source_id`. Tables mutées : `carbon_footprint` (INSERT via `POST /me/carbon/compute` existant + nouveaux `edit-line` et `recompute` qui appellent le même `service.compute_footprint` en interne) et `audit_event` (INSERT via `record_audit`). **Aucune nouvelle table, aucune migration.**

**Testing** :

- Frontend (vitest + `@vue/test-utils`) — unit :
  - Composables : `useCarbonStore.test.ts`, `useCarbon.test.ts`, `useCarbonHistory.test.ts`, `useCarbonEdit.test.ts`, `useCarbonWizard.test.ts`.
  - Helpers : `groupCarbonByScope.test.ts`, `computeCarbonCoverage.test.ts`.
  - Composants : `CarbonOverview.test.ts`, `ScopeDonut.test.ts`, `EvolutionLineChart.test.ts`, `ScopeAccordion.test.ts`, `EmissionLine.test.ts`, `FactorSourcePopover.test.ts`, `RecalcStrip.test.ts`, `EditLineDrawer.test.ts`, `LowCoverageBanner.test.ts`, `EmptyStateWizard.test.ts`, `FactorReferentielSwitch.test.ts`.
- E2E (Playwright, `frontend/tests/e2e/`) :
  - (a) ouverture `/carbone` avec empreinte courante et N-1 → KPI total + donut + delta % + couverture % visibles sans scroll, LCP < 1.8 s.
  - (b) déplier Scope 1 → 3 postes (combustion fixe / mobile / fugitives) avec valeur, unité, facteur (version + valid_from) et pin source cliquable.
  - (c) déplier Scope 2 électricité → infobulle "market vs location-based" présente.
  - (d) éditer ligne S2 électricité 50 000 kWh → bottom sheet `ask_form` ouverte → soumettre 45 000 kWh + source "facture EDF mars 2026" → ligne mise à jour + KPI total recalculé + delta % visible < 2 s + audit ligne enregistrée (`source_of_change = manual`, vérifié via API audit).
  - (e) tenter d'éditer une ligne sans renseigner de source → soumission refusée + message "Source obligatoire pour toute donnée carbone".
  - (f) cliquer "Recalculer" sur 30 lignes → spinner global + bouton désactivé + au retour < 2 s, horodatage "Dernier calcul" mis à jour.
  - (g) couverture < 60 % → bannière d'avertissement visible avec CTA "Compléter".
  - (h) absence de N-1 → delta affiché "—" + libellé "Pas de comparaison disponible".
  - (i) compte vide → wizard 3 étapes (énergie → déplacements → achats) à la place de la synthèse, progression visible.
  - (j) wizard interrompu à mi-parcours puis retour sur `/carbone` → réponses partielles restaurées depuis `localStorage`.
  - (k) wizard complété → bilan calculé, wizard fermé, synthèse visible avec les nouvelles données.
  - (l) sync chat : depuis un autre onglet, déclencher mutation `entity_updated{carbon_footprint}` → ligne et KPIs mis à jour < 1 s sans rechargement.
  - (m) recalcul échoué (mock backend 500) → message d'erreur français explicite + état précédent préservé.
  - (n) `prefers-reduced-motion: reduce` → animations donut/drawer/wizard désactivées.
  - (o) switch facteurs ADEME/IPCC (P2) → désactivé au MVP avec infobulle "À venir" ; couvert par un test de présence du badge "Estimation, pas référence officielle" et de la propriété `disabled`.
- Backend (`backend/tests/carbon/`) — trois nouveaux fichiers :
  - `test_index_endpoint.py` : (1) compte sans empreinte → 200 + liste vide ; (2) compte avec 3 années (2024, 2025, 2026) → 3 entrées triées desc par year ; (3) compte avec 2 calculs sur la même année → seule la dernière empreinte par year retournée (la plus récente `computed_at`) ; (4) cross-tenant → la requête ne renvoie que les empreintes du tenant courant ; (5) JWT manquant → 401.
  - `test_recompute_endpoint.py` : (1) année sans empreinte → 404 `footprint_not_found` ; (2) année avec empreinte → nouvelle row `carbon_footprint` créée avec `source_data_json` identique au précédent et `version` incrémenté ; (3) facteur révoqué entre les deux calculs → relookup utilise la nouvelle version active, le total change, l'audit est journalisé (`source_of_change = manual`) ; (4) cross-tenant → 404 ; (5) JWT manquant → 401.
  - `test_edit_line_endpoint.py` : (1) ligne existante S2 électricité → quantité modifiée, nouvelle empreinte créée, breakdown reflète la nouvelle valeur, audit OK ; (2) `source_id` manquant → 422 `validation_error` ; (3) `source_id` non vérifié → 400 `source_not_verified` ; (4) `code` ligne inexistant dans le dernier `source_data_json` → la ligne est **ajoutée** (pas écrasée) avec la quantité fournie ; (5) cross-tenant → 404 ; (6) `quantity < 0` → 422 ; (7) JWT manquant → 401.
  - Plus tests d'extension de schéma : `test_carbon_source_item_source_id.py` couvrant rétrocompatibilité (`source_id=None` accepté par `POST /me/carbon/compute` historique).

**Target Platform** : Web responsive — desktop ≥ 1366×768 (synthèse en grid 3 colonnes : KPI/donut/courbe + drilldown 2 colonnes), tablette 768–1365 px (synthèse 2 colonnes empilées + drilldown 1 colonne + drawer 80 % largeur), mobile < 768 px (synthèse empilée verticalement + accordéon + drawer plein écran).

**Project Type** : Web application (Nuxt 4 frontend + FastAPI backend). Mono-repo existant.

**Performance Goals** :

- LCP `/carbone` < 1.8 s p95 sur 4G typique pour une empreinte de 30 lignes (NFR-001 brief, SC-007 spec).
- Recalcul global rendu < 2 s pour 30 lignes (NFR-002 brief, SC-004 spec).
- Édition d'une ligne → vue synthèse rafraîchie sans rechargement complet en < 2 s p95 (SC-002).
- Drilldown accordéon : ouverture < 100 ms même pour 30 lignes (sans virtualisation au MVP). Au-delà de 100 lignes, virtualisation activée (FR-016) via le composant existant `<UiVirtualList>` de F37 si dispo, sinon fallback `v-show` + lazy loading des `<VizSourcePin>` au hover.
- Switch référentiel facteurs (P2, MVP désactivé) : objectif < 1 s post-implémentation backend (SC-003).
- Sync chat → mise à jour ciblée < 1 s (SC-009).
- Animations : donut gsap fade-in 200 ms, drawer slide-in 250 ms, transitions wizard 200 ms ; toutes désactivées si `prefers-reduced-motion: reduce` (SC-008).

**Constraints** :

- **P1 Sourcing** : chaque ligne d'émission DOIT exposer le facteur d'émission appliqué (valeur + unité + version + valid_from) et un pin `<VizSourcePin>` pointant vers la `Source` `verified` correspondante via `source_id`. Aucune ligne sans `source_id` n'est créée par l'UI (FR-011). Les données historiques importées sans `source_id` (avant F47) sont affichées avec un badge "Source manquante" + CTA "Compléter".
- **P3 Audit** : chaque édition de ligne et chaque recalcul global enregistrent une entrée `audit_event` avec `entity = "carbon_footprint"`, `field = "edit-line"|"recompute"`, `source_of_change = "manual"`, `old`/`new` (pour edit-line : ancienne et nouvelle quantité). Géré par `record_audit` côté service.
- **P4 Versioning** : la version du facteur d'émission utilisée à chaque calcul est lue depuis `factor_versions_json` de `CarbonFootprint` ; affichée dans la popover détail facteur. Un facteur révisé entre N-1 et N implique deux versions distinctes — la donnée historique conserve **son** `factor_version` (jamais réécrite). C'est garanti par le snapshot `breakdown_json` immuable.
- **P5 Money/Decimal typé** : tous les `kgCO2e`, `tCO2e`, `factor_value`, `quantity` exposés par l'API sont des `Decimal` (string en JSON) ; le frontend utilise `decimal.js` pour la conversion `kgCO2e → tCO2e` (`/ 1000` exact) et l'agrégation des sommes par scope. Le formatage final (2 décimales `tabular-nums`) se fait via `useDecimal().format()`.
- **P8 Édition manuelle + sync LLM** : l'édition manuelle d'une ligne via `POST .../edit-line` invalide le contexte LLM (signal émis sur l'EventBus `context_invalidated{entity: "carbon_footprint", account_id}` — pattern partagé avec F46). À l'inverse, une mutation LLM côté chat émet `entity_updated{carbon_footprint}` qui rafraîchit la page si elle est ouverte.
- **P10 Bottom sheet** : aucune saisie inline. Édition d'une ligne, wizard 3 étapes, switch unité, ajout d'un poste manquant — tout passe par `<ChatBottomSheet>` + `<ShowForm>`. Bouton "Répondre librement" présent dans le wizard pour basculer en saisie texte libre.

**Scale/Scope** : 30 lignes typiques au MVP (3 S1 + 4 S2 + 5 S3 + extras). Au-delà de 100 lignes, virtualisation. Empreintes archivées : 5 ans de données par tenant (1 ligne carbon_footprint par année + N recalculs intermédiaires). Index multi-année plafonné à 10 ans côté query.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Toute donnée factuelle introduite par cette feature pointe-t-elle vers une `Source` `verified` ? Les nouveaux champs catalogue ont-ils `source_id NOT NULL` ? | ✅ Chaque ligne créée par l'UI porte un `source_id` non null vérifié côté backend (`POST .../edit-line` rejette `source_id` absent ou non `verified`). `POST /me/carbon/compute` historique conserve `source_id: UUID \| None` pour rétrocompat — la nouvelle UI n'émet jamais de NULL. Pin `<VizSourcePin>` exposé sur 100 % des lignes affichées. |
| P2 | Multi-tenant RLS | Toute nouvelle table métier porte-t-elle `account_id` + politique RLS ? Les accès cross-tenant retournent-ils 404 ? | ✅ Aucune nouvelle table. `carbon_footprint` (existante F28) porte déjà `account_id` + RLS (P2 vérifié à la migration `0001`). Les trois nouveaux endpoints sont RLS-aware via `Depends(get_current_pme)` + filtre `account_id`. Cross-tenant testé → 404. |
| P3 | Audit log append-only | Toute mutation introduite est-elle journalisée avec `source_of_change` ∈ {manual, llm, import, admin} ? | ✅ `edit-line` et `recompute` appellent `record_audit(entity="carbon_footprint", source_of_change=SourceOfChange.MANUAL, old=..., new=...)`. Le `compute` historique est déjà audité par F28. Aucun UPDATE/DELETE introduit (append-only). |
| P4 | Versioning + snapshot candidatures | Les nouveaux référentiels/critères/formules portent-ils `version`, `valid_from`, `valid_to` ? Les candidatures stockent-elles un `snapshot_json` immuable ? | ✅ Aucun nouveau référentiel introduit ; les `facteur_emission` consommés sont déjà versionnés (F09). Chaque empreinte stocke `factor_versions_json` immuable (snapshot existant). Aucune réécriture rétroactive — chaque édition crée une **nouvelle** row `carbon_footprint`. |
| P5 | Money typé | Toute valeur monétaire utilise-t-elle `Money = {amount: Decimal, currency}` ? Le risque de change est-il rendu explicite ? | ✅ Aucune valeur monétaire dans cette feature (uniquement quantités physiques + facteurs d'émission). Les `Decimal` sont utilisés pour `quantity`, `factor_value`, `kgCO2e`, `tCO2e` — pas de `float`. |
| P6 | Pivot Indicateur unique | Les données ESG sont-elles stockées comme valeurs d'`Indicateur` (pas par axe E/S/G ni dupliquées par référentiel) ? | ✅ L'empreinte carbone est un domaine spécifique avec son propre modèle (`carbon_footprint`) ; elle n'est pas dupliquée par référentiel ESG. Le mapping vers les indicateurs ESG (axe E) est fait en aval par le scoring (F23), pas par F47. |
| P7 | Plateforme fermée aux intermédiaires | La feature évite-t-elle tout rôle utilisateur Intermédiaire/Bank/Fund ? Les sorties externes passent-elles par attestation Ed25519 + QR ? | ✅ La page `/carbone` est strictement réservée au rôle PME. L'export PDF (US9, P2) passera par le mécanisme d'attestation F30 / F51 — hors scope de ce plan. |
| P8 | Édition manuelle + sync LLM | Tout champ alimenté par le LLM est-il modifiable manuellement ? La mutation manuelle invalide-t-elle le contexte LLM en temps réel ? | ✅ Toute ligne, qu'elle ait été créée par le chat (LLM) ou par l'UI, est éditable via `EditLineDrawer.vue` → `POST .../edit-line`. L'édition émet `context_invalidated{carbon_footprint}` sur l'EventBus, capté par le chat pour vider son contexte sur cette entité. Inverse : `entity_updated` rafraîchit la page (US7). |
| P9 | Tool-use LLM fiable | Nouveaux tools : nom verbal, "use when / don't use when", schéma Pydantic strict (`extra='forbid'`), ≤ 10 tools concurrents par tour, eval gating planifié ? | ✅ Aucun nouveau tool LLM introduit par F47. Les tools `get_carbon_footprint`, `update_carbon_data`, `compute_carbon_footprint` existent côté F28 et restent inchangés. |
| P10 | UX bottom sheet | Les composants interactifs vivent-ils dans le bottom sheet (jamais inline dans la bulle LLM) ? Bouton "Répondre librement" présent ? | ✅ Édition d'une ligne, wizard empty-state 3 étapes, switch d'unité — tout passe par `<ChatBottomSheet>` + `<ShowForm>` (`ask_form`). Aucune saisie inline. Bouton "Répondre librement" présent dans le wizard pour basculer en saisie libre. |

**Verdict gate Phase 0** : ✅ Tous les principes passent. Aucun blocage. Pas de section Complexity Tracking nécessaire.

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ; LLM via OpenRouter ; embeddings Voyage `voyage-3.5` (1024 dim).
- Dev local : backend en `.venv`, Postgres seul service dockerisé, frontend en `pnpm dev`.
- Hébergement production : Europe ou Afrique de l'Ouest uniquement.
- Conformité : RGPD + loi ivoirienne 2013-450 + UEMOA 20/2010 dès le MVP.
- Langue : français par défaut.

## Project Structure

### Documentation (this feature)

```text
specs/047-empreinte-carbone-ui/
├── plan.md              # Ce fichier
├── research.md          # Phase 0 — décisions techniques (édition de ligne via re-snapshot, wizard persistance, switch P2)
├── data-model.md        # Phase 1 — modèle conceptuel (carbon_footprint relu, virtual carbon_line, scope/poste/coverage)
├── quickstart.md        # Phase 1 — démo manuelle (3 terminaux + parcours bout-en-bout)
├── contracts/           # Phase 1 — contrats des 3 nouveaux endpoints + extension CarbonSourceItem
│   ├── backend-index-endpoint.md
│   ├── backend-recompute-endpoint.md
│   ├── backend-edit-line-endpoint.md
│   ├── frontend-api-consumption.md
│   ├── frontend-components.md
│   └── chat-eventbus-sync.md
├── checklists/
│   └── requirements.md  # Spec quality checklist (déjà créée par /speckit-specify)
└── tasks.md             # Phase 2 (créé par /speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   └── carbon/
│       ├── __init__.py        # existant
│       ├── engine.py          # existant — pas modifié
│       ├── plan.py            # existant — pas modifié
│       ├── router.py          # MODIFIÉ : +3 endpoints (index, recompute, edit-line)
│       ├── schemas.py         # MODIFIÉ : +source_id sur CarbonSourceItem (None par défaut), +CarbonIndexEntryOut, +CarbonEditLineRequest, +CarbonRecomputeResponse
│       └── service.py         # MODIFIÉ : +list_index, +recompute (rejoue compute avec source_data_json), +edit_line (reconstruit source_data + applique mutation + appelle compute_footprint)
└── tests/
    └── carbon/
        ├── __init__.py
        ├── test_index_endpoint.py        # nouveau
        ├── test_recompute_endpoint.py    # nouveau
        ├── test_edit_line_endpoint.py    # nouveau
        └── test_carbon_source_item_source_id.py  # nouveau (rétrocompat schéma)

frontend/
├── app/
│   ├── pages/
│   │   └── carbone/
│   │       └── index.vue                 # nouveau — page synthèse + drilldown + édition + recalcul + wizard
│   ├── components/
│   │   └── carbone/
│   │       ├── CarbonOverview.vue        # KPI total + delta N-1 + couverture %
│   │       ├── ScopeDonut.vue            # donut Scope 1/2/3
│   │       ├── EvolutionLineChart.vue    # courbe annuelle N vs N-1
│   │       ├── ScopeAccordion.vue        # accordéon par scope
│   │       ├── EmissionLine.vue          # ligne d'activité (valeur + unité + facteur + pin source)
│   │       ├── FactorSourcePopover.vue   # popover détail facteur version + valid_from
│   │       ├── RecalcStrip.vue           # bouton recalculer + horodatage
│   │       ├── EditLineDrawer.vue        # orchestrateur bottom sheet édition ligne
│   │       ├── LowCoverageBanner.vue     # avertissement < 60 %
│   │       ├── EmptyStateWizard.vue      # wizard 3 étapes
│   │       ├── FactorReferentielSwitch.vue # P2 — désactivé MVP avec badge "Estimation"
│   │       └── ExportPdfButton.vue       # P2 — dépend F51
│   ├── composables/
│   │   ├── useCarbon.ts
│   │   ├── useCarbonHistory.ts
│   │   ├── useCarbonEdit.ts
│   │   ├── useCarbonWizard.ts
│   │   └── __tests__/
│   │       ├── useCarbon.test.ts
│   │       ├── useCarbonHistory.test.ts
│   │       ├── useCarbonEdit.test.ts
│   │       └── useCarbonWizard.test.ts
│   ├── lib/
│   │   ├── groupCarbonByScope.ts          # CARBON_EXPECTED_POSTS_BY_SCOPE + groupage
│   │   ├── computeCarbonCoverage.ts
│   │   └── __tests__/
│   │       ├── groupCarbonByScope.test.ts
│   │       └── computeCarbonCoverage.test.ts
│   ├── services/api/
│   │   └── carbon.ts                      # client API frontend (fetch index, footprint, recompute, edit-line)
│   ├── stores/
│   │   ├── carbon.ts                      # useCarbonStore
│   │   └── __tests__/
│   │       └── carbon.test.ts
│   ├── types/
│   │   └── carbon.ts                      # types TS miroirs des schémas Pydantic
│   └── locales/
│       └── fr.ts                          # MODIFIÉ : +clés `carbon.*` (titres, KPIs, wizard, erreurs)
└── tests/
    └── e2e/
        └── carbone.spec.ts                # nouveau — 15 scénarios bout-en-bout
```

**Structure Decision** : conserve la structure mono-repo (backend + frontend) déjà en place. Pas de package frontend séparé, pas de monorepo nx. Les 3 ajouts backend sont localisés dans le seul package `app/carbon/`. Le frontend ajoute un dossier dédié `pages/carbone/` + `components/carbone/` + helpers/types/store/composables, en miroir du pattern F46 (`pages/scoring/`, `components/scoring/`).

## Complexity Tracking

> Aucun écart à la constitution — section vide.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(aucune)_ | _(N/A)_ | _(N/A)_ |
