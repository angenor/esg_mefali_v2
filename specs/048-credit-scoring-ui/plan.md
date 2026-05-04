# Implementation Plan: Credit scoring UI (F48)

**Branch**: `048-credit-scoring-ui` | **Date**: 2026-05-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/048-credit-scoring-ui/spec.md`

## Summary

Livrer la page **`/credit-score`** : UI dédiée à la consultation et au pilotage du score crédit ESG d'une PME (gauge 0-100 avec classification, 4 sous-scores, badges d'éligibilité aux financements verts, recommandations actionnables, recalcul animé, historique 6 derniers calculs, wizard onboarding 4 étapes), branchée sur le backend **F29** déjà déployé (`GET /me/credit-score`, `POST /me/credit-score/recompute`, `POST /me/credit-data`, `POST /me/credit-data/mobile-money`, `GET /methodologie/credit-scoring`).

La feature est très majoritairement **frontend** mais nécessite **trois ajouts backend ciblés** plus une **extension non rétro-incompatible** du schéma `CreditScoreOut`, parce que F29 :

- N'expose **aucun endpoint d'historique** (US7).
- N'expose **aucun calcul d'éligibilité** par dispositif vert (US3).
- Expose les facteurs sous forme `facteurs: list[dict]` avec un champ `axis ∈ {financiere, environnementale, gouvernance, sociale}`, **pas** les 4 sous-scores demandés par la spec UI (Solidité financière, Performance opérationnelle, Engagement ESG, Gouvernance — cf. décision tranchée en research.md sur le mapping et l'agrégation).

Ajouts backend :

1. `GET /me/credit-score/history?limit=6` — index append-only des `credit_score` de l'entreprise courante, lecture seule, RLS-aware, sans audit. Paramètre `limit` borné `[1..24]`, défaut `6` (US7, FR-011).
2. `GET /me/credit-score/eligibility` — évalue à la volée l'éligibilité de la PME courante à un catalogue de dispositifs (BOAD-vert, SUNREF, Ecobank-Green-Lending, plus dispositifs ajoutés ultérieurement) à partir du dernier `credit_score` et du profil entreprise. Lecture seule, RLS-aware, sans audit. Catalogue versionné déclaratif côté backend (`backend/app/credit/eligibility_catalog.py`) avec `valid_from`/`valid_to` et `source_id` (P1, P4) — la liste fournie est **dynamique** côté front (cf. clarification Q3) ; le MVP garantit a minima les 3 dispositifs nommés.
3. `GET /me/credit-score/recommendations?limit=5` — sélectionne dans les actions du plan d'action **F45** celles dont `target_subscore` est rattaché au sous-score crédit le plus faible, triées par `estimated_credit_points_impact` décroissant (cf. clarification Q1). Lecture seule. Le contrat exige que F45 expose déjà `target_subscore: 'financiere'|'operationnelle'|'esg'|'gouvernance'|null` et `estimated_credit_points_impact: int|null` sur les `ActionItemOut` (à valider en Phase 0 — sinon ce champ devient un ajout F45 mineur, voir research.md décision R-04).

Extension `CreditScoreOut` : ajout d'un champ optionnel `subscores: dict[str, int]` (4 clés `solidite_financiere`, `performance_operationnelle`, `engagement_esg`, `gouvernance`, chacune ∈ `[0..100]`) calculé côté `service.recompute_score`/`service.get_latest_score` à partir des `facteurs` existants et d'une table de mapping factor_name→subscore_bucket déclarée en pure data dans `backend/app/credit/subscore_mapping.py`. Aucune migration de DB : `subscores` est dérivé à la volée depuis `facteurs` (déjà persistés via `combine`/`solvabilite`/`impact_vert` + `factor_breakdown` en JSONB du score). Pour les anciennes lignes ne couvrant pas les 4 buckets, on retourne la valeur `null` pour le bucket manquant — l'UI affiche alors « non calculé » (US2 AS2). Aucune nouvelle table, aucune migration Alembic.

À ces ajouts s'ajoutent deux contraintes UI fortes propres à F48 :

- **Couverture partielle** (FR-012a, clarification Q4) : si seuls les 4 montants financiers (CA, EBE, dette, fonds propres) sont fournis et que les volets ESG/Gouvernance manquent, le backend renvoie quand même un `combine` calculable avec une `coherence_warning=true` (déjà présent sur `CreditScoreOut`) ; l'UI affiche un bandeau « Couverture partielle » et marque les sous-scores manquants `null`.
- **Seuils de classification fixes** (FR-001, clarification Q2) : Insuffisant `0-39`, À améliorer `40-59`, Bon `60-79`, Excellent `80-100`, bornes inférieures inclusives. Le mapping est implémenté **côté front** dans un helper pur (`lib/classifyCreditScore.ts`) — pas de duplication backend pour rester localisable et testable, mais documenté dans research.md comme contrat partagé front/back.

Ajouts frontend :

- 1 page Nuxt : `pages/credit-score/index.vue` (synthèse + sous-scores + badges + recommandations + historique + wizard empty-state ; pas de sous-route — tout vit sous `/credit-score`).
- 1 famille de composants `components/credit-score/*` :
  - **Synthèse** : `GaugeHero.vue` (gauge gsap 0-100 + classification + delta N-1), `ClassificationLabel.vue` (libellé + couleur + texte alternatif daltonien-friendly), `PartialCoverageBanner.vue` (bandeau « Couverture partielle » FR-012a).
  - **Décomposition** : `SubScoreCard.vue` (×4 — valeur 0-100 + barre + état « non calculé » avec CTA), `SubScoreGrid.vue` (layout 2×2 desktop / pile mobile).
  - **Éligibilité** : `EligibilityBadge.vue` (badge éligible/non éligible avec **raison principale** uniquement — clarification Q5), `EligibilityDetailModal.vue` (`<UiModal>` avec liste exhaustive des critères satisfaits/non satisfaits + lien matching F53).
  - **Recommandations** : `RecommendationList.vue` (3-5 cartes priorisées), `RecommendationCard.vue` (action + impact estimé « +X points » avec mention « estimation » P1).
  - **Saisie & recalcul** : `CreditDataDrawer.vue` (orchestre l'ouverture du bottom sheet `ask_form` multi-étapes CA/EBE/dette/fonds propres avec montants typés `Money` P5), `RecalcStrip.vue` (horodatage « Dernier calcul » + bouton recalc manuel + spinner).
  - **Historique** : `ScoreHistoryChart.vue` (`<VizLineChart>` 6 derniers calculs avec hover date/valeur/version méthodologie).
  - **Empty state** : `EmptyStateWizard.vue` (déclenche le wizard 4 étapes via `<ChatBottomSheet show_form>` avec persistance localStorage — étapes Financier→ESG→Gouvernance→Récap).
  - **P2** : `ExportPdfButton.vue` (P2, dépend F51 — désactivé au MVP avec infobulle « À venir »).

- 1 store Pinia `useCreditScoreStore` : score courant, sous-scores, éligibilité catalogue+statuts, historique 6 derniers calculs, état loading/error, mode wizard, dernier `computed_at`, version méthodologie utilisée.
- 5 composables :
  - `useCreditScore` (orchestre fetch score + sous-scores + abonnement EventBus chat `entity_updated{credit_data, credit_score}`).
  - `useCreditEligibility` (fetch et mémorise la liste catalogue, expose `byCode(code)` pour rendu badges, gère le clic « voir détail » → ouvre `EligibilityDetailModal`).
  - `useCreditHistory` (fetch des 6 derniers calculs, dérive `delta_n1` côté client, cache 60 s).
  - `useCreditEdit` (orchestre bottom sheet `ask_form` multi-étapes, soumet `POST /me/credit-data` + déclenche `POST /me/credit-score/recompute`, met à jour le store et émet `entity_updated{credit_data, credit_score}`).
  - `useCreditWizard` (gère le wizard empty-state 4 étapes avec persistance localStorage des réponses partielles, soumet en bloc à la fin).

- 3 helpers purs :
  - `lib/classifyCreditScore.ts` : `classify(score: number): {bucket: 'insuffisant'|'a_ameliorer'|'bon'|'excellent', label: string, colorToken: string}` — implémente les seuils 80/60/40 (clarification Q2).
  - `lib/selectCreditRecommendations.ts` : tri/filtre côté client à partir de la réponse backend (filet de sécurité si le backend retourne plus de 5 actions ou si elles ne sont pas pré-triées) — clarification Q1.
  - `lib/animateGaugeTransition.ts` : tween gsap 320 ms entre l'ancien score et le nouveau ; respecte `prefers-reduced-motion: reduce` (FR-009, NFR-003 du brief).

- Réutilisation **maximale** des primitives F36/F37/F39/F40/F41/F46/F47 : `<UiCard>`, `<UiBadge>`, `<UiButton>`, `<UiSkeleton>`, `<UiEmptyState>`, `<UiModal>`, `<UiBanner>` (couverture partielle), `<UiNumber money>` (saisies financières — P5), `<ChatBottomSheet>` + `<ShowForm ask_form>` (wizard 4 étapes + édition multi-step), `<VizLineChart>` (historique), `<VizSourcePin>` (sources facteurs/dispositifs), `<VizGaugeChart>` si livré par F40, sinon implémentation locale en SVG + gsap (à vérifier en research.md décision R-05). Aucune nouvelle bibliothèque graphique.

- Branchement EventBus chat ↔ credit-score : à la réception d'`entity_updated{credit_data}` ou `entity_updated{credit_score}`, invalidation **ciblée** du score courant + sous-scores + historique. Inversement, toute modification locale (bottom sheet financier, recalcul manuel, fin de wizard) émet `entity_updated{credit_data, credit_score}` pour propager aux autres surfaces (chat F41, dashboard F44 carte score crédit, mini-card scoring F46).

- La page **réutilise** les patterns de F46/F47 (store + composables + bottom sheet + EventBus), garantissant la cohérence d'expérience.

Côté backend, les trois ajouts sont **append-only en lecture pure** (sauf `recompute` existant qui INSERT déjà), RLS-aware, audit-loggés là où l'écriture existe (déjà fait par F29 pour `submit_credit_data` et `recompute_score`), accompagnés de tests `pytest` (unit + integration). Le catalogue d'éligibilité (déclaratif, versionné) inclut un `source_id` par dispositif pointant vers une `Source` `verified` (extrait du document de référence du dispositif — BOAD, SUNREF AFD, Ecobank Green Lending) pour respecter P1.

## Technical Context

**Language/Version** : TypeScript 5.x + Vue 3 / Nuxt 4 (frontend) ; Python 3.12 (backend, **trois nouveaux endpoints + une extension de schéma**).

**Primary Dependencies** :

- Frontend (déjà installés en F36–F47) : Nuxt 4, Pinia, Tailwind v4, gsap (animation gauge + transitions wizard/drawer), `chart.js` (historique via `viz/`), `decimal.js` (P5 — montants financiers du bottom sheet en `Decimal`). Composables existants `useChatEventBus`, `useChatBottomSheet`, `useToast`, `useReducedMotion`, `useT`, `useAuth`, `useSourceFetch`, `useDecimal`, `useMoneyFormat`, `useChartTheme`. Pattern Pinia identique à `useScoringStore` (F46) et `useCarbonStore` (F47).
- Backend : aucune nouvelle dépendance Python ; on s'appuie sur SQLAlchemy + Pydantic v2 déjà présents et sur `app.audit.record_audit` + `app.credit.service` déjà utilisés.

**Storage** : PostgreSQL 16 + pgvector (déjà). Tables consommées en lecture : `credit_score` (append-only, F29), `credit_data` (F29), `entreprise` (F11) pour le profil sectoriel/taille servant à l'évaluation d'éligibilité, `source` (catalogue F09) pour les pastilles. Tables mutées : `credit_data` (INSERT via `POST /me/credit-data` existant), `credit_score` (INSERT via `POST /me/credit-score/recompute` existant), `audit_event` (INSERT via `record_audit`, déjà fait par F29). **Aucune nouvelle table, aucune migration.** Le catalogue d'éligibilité vit comme module Python pure (`backend/app/credit/eligibility_catalog.py`) — décision documentée dans research.md (R-02).

**Testing** :

- Frontend (vitest + `@vue/test-utils`) — unit :
  - Composables : `useCreditScore.test.ts`, `useCreditEligibility.test.ts`, `useCreditHistory.test.ts`, `useCreditEdit.test.ts`, `useCreditWizard.test.ts`.
  - Helpers : `classifyCreditScore.test.ts` (tous les cas de bord — 0, 39, 40, 59, 60, 79, 80, 100), `selectCreditRecommendations.test.ts`, `animateGaugeTransition.test.ts` (mock gsap, vérifie que `prefers-reduced-motion` court-circuite l'animation).
  - Store : `creditScore.test.ts` (état initial, hydratation, invalidations EventBus, mode wizard).
  - Composants : `GaugeHero.test.ts`, `ClassificationLabel.test.ts` (texte alternatif présent FR-015), `PartialCoverageBanner.test.ts`, `SubScoreCard.test.ts`, `SubScoreGrid.test.ts`, `EligibilityBadge.test.ts`, `EligibilityDetailModal.test.ts`, `RecommendationList.test.ts`, `RecommendationCard.test.ts`, `CreditDataDrawer.test.ts`, `RecalcStrip.test.ts`, `ScoreHistoryChart.test.ts`, `EmptyStateWizard.test.ts`, `ExportPdfButton.test.ts` (badge "À venir" P2).

- E2E (Playwright, `frontend/tests/e2e/`) :
  - (a) `credit-score-overview-render.spec.ts` — score 72 + N-1 64 → gauge animée à 72, classification « Bon », delta « +8 points », LCP < 1.5 s.
  - (b) `credit-score-classification-thresholds.spec.ts` — score 60 → « Bon », score 59 → « À améliorer », score 80 → « Excellent », score 39 → « Insuffisant ».
  - (c) `credit-score-subscores-render.spec.ts` — 4 cartes avec valeurs et barres ; sous-score `null` → carte « non calculé » + CTA « Compléter mes données ».
  - (d) `credit-score-eligibility-badges.spec.ts` — éligible BOAD-vert + SUNREF + non éligible Ecobank → 3 badges avec leurs états et raisons principales.
  - (e) `credit-score-eligibility-modal.spec.ts` — clic sur badge non éligible → modal liste exhaustive critères satisfaits/non satisfaits + bouton « Voir les offres compatibles » (pour éligible).
  - (f) `credit-score-recommendations-flow.spec.ts` — au moins 3 recommandations avec impact estimé « +X points » + mention « estimation » + clic redirige vers `/plan-action#step-{id}`.
  - (g) `credit-score-edit-data-flow.spec.ts` — clic « Mettre à jour » → bottom sheet 4 étapes CA/EBE/dette/fonds propres → soumission → gauge anime ancien→nouveau → toast « +N points » → audit ligne enregistrée (`source_of_change=manual`).
  - (h) `credit-score-edit-money-validation.spec.ts` — montant sans devise refusé, montant non numérique refusé, valeurs aberrantes < 0 refusées avec message clair, autres saisies préservées.
  - (i) `credit-score-recalc-failure.spec.ts` — backend mock 500 → message d'erreur français + gauge reste sur valeur précédente, pas d'état intermédiaire.
  - (j) `credit-score-history-render.spec.ts` — 6 calculs → courbe linéaire ordonnée chrono ; 1 seul calcul → message « Premier calcul ».
  - (k) `credit-score-empty-state-wizard.spec.ts` — compte sans score → wizard 4 étapes ; complété < 3 min → premier score affiché ; interruption à mi-parcours → reprise depuis localStorage.
  - (l) `credit-score-partial-coverage.spec.ts` — financier renseigné mais ESG manquant → bandeau « Couverture partielle » + sous-score ESG « non calculé ».
  - (m) `credit-score-chat-sync.spec.ts` — depuis un autre onglet, mutation `entity_updated{credit_score}` → gauge anime sans rechargement.
  - (n) `credit-score-color-blind-friendly.spec.ts` — désactivation des couleurs (filtre CSS) → classification reste lisible par texte (FR-015).
  - (o) `credit-score-reduced-motion.spec.ts` — `prefers-reduced-motion: reduce` → animation gauge désactivée, transition instantanée.
  - (p) `credit-score-recommendation-deadlink.spec.ts` — recommandation pointant vers étape de plan inexistante → redirection vers racine `/plan-action` (edge case).

- Backend (`backend/tests/credit/`) — trois nouveaux fichiers + un fichier d'extension :
  - `test_history_endpoint.py` : (1) compte sans calcul → 200 + `{items: []}` ; (2) compte avec 3 calculs → 3 entrées triées desc par `computed_at` ; (3) compte avec 10 calculs → `limit=6` par défaut, `limit=12` respecté ; (4) `limit=0` ou `limit=25` → 422 ; (5) cross-tenant → seules les lignes du tenant ; (6) JWT manquant → 401.
  - `test_eligibility_endpoint.py` : (1) compte sans score → 200 avec items `status="incomplete"` (motif « Score crédit non calculé ») ; (2) score 72 + secteur autorisé BOAD → BOAD-vert `eligible` ; (3) score 45 → BOAD-vert `not_eligible` avec `primary_reason="score_below_threshold"` et `criteria` exhaustifs ; (4) cross-tenant → seuls les dispositifs du catalogue retournés et statuts évalués sur le tenant courant ; (5) JWT manquant → 401 ; (6) catalogue vide (mock) → 200 avec liste vide ; (7) `source_id` présent et `verified` sur chaque dispositif (P1) ; (8) chaque dispositif a `version` et `valid_from/valid_to` (P4).
  - `test_recommendations_endpoint.py` : (1) compte sans plan d'action → 200 + liste vide ; (2) plan d'action avec 8 actions, dont 3 ciblées sur le sous-score le plus faible → top 3-5 retournées triées impact desc (clarification Q1) ; (3) `limit=3` → max 3 ; (4) `limit=10` → 422 (max 5) ; (5) cross-tenant → seules les actions du tenant ; (6) actions sans `estimated_credit_points_impact` → exclues (graceful skip) ; (7) JWT manquant → 401.
  - `test_subscores_extension.py` (extension `CreditScoreOut.subscores`) : (1) `recompute_score` retourne `subscores` non vide ; (2) `subscores` cohérents avec la moyenne pondérée des `facteurs` mappés ; (3) bucket sans facteur disponible → `subscores[bucket] is None` ; (4) rétrocompat — clients ne passant pas `subscores` dans leurs assertions continuent de fonctionner (le champ est additif, ConfigDict ne casse pas) ; (5) `subscores` chacun ∈ `[0..100]` ou `None`.

**Target Platform** : Web responsive — desktop ≥ 1366×768 (gauge en hero pleine largeur + sous-scores 4 colonnes + badges en ligne + recommandations en cartes + historique en bas), tablette 768–1365 px (gauge centrée + sous-scores 2×2 + badges empilés + drawer 80 %), mobile < 768 px (gauge réduite + sous-scores empilés + badges accordéon + drawer plein écran avec bouton fermer en haut).

**Project Type** : Web application (Nuxt 4 frontend + FastAPI backend). Mono-repo existant.

**Performance Goals** :

- LCP `/credit-score` < 1.5 s p95 sur 4G typique avec 6 calculs historiques + 4 sous-scores + 3 dispositifs (NFR-001 brief, SC-001 spec).
- Animation gauge gsap : tween 320 ms ancien→nouveau, 60 fps p95 desktop et mobile (FR-003 brief, NFR-003, SC-007). Désactivée si `prefers-reduced-motion: reduce`.
- Recalcul manuel → vue rafraîchie sans rechargement complet en < 2 s p95 (SC-002).
- Wizard empty-state complet en < 3 min sur mobile (NFR-002 brief, SC-006).
- Sync chat → mise à jour ciblée < 1 s (SC-009).
- Switch entre carte de sous-score et modal éligibilité < 200 ms (perception instantanée, SC-004 « moins de 2 interactions »).
- Animations annexes : modal slide-in 250 ms, drawer slide-in 250 ms, bandeau couverture fade-in 200 ms ; toutes désactivées si `prefers-reduced-motion: reduce`.

**Constraints** :

- **P1 Sourcing** : chaque dispositif d'éligibilité DOIT exposer un `source_id` pointant vers une `Source` `verified` (document officiel BOAD/SUNREF/Ecobank). Le détail des critères dans la modal expose la même `<VizSourcePin>`. Chaque facteur de scoring affiché dans les sous-scores hérite de son `source_id` via `facteurs` du `CreditScoreOut` existant. Le bandeau « Couverture partielle » indique explicitement quelles données manquent (FR-012a) et pointe vers la collecte. La méthodologie (poids alpha/beta, formules) reste consultable via `GET /methodologie/credit-scoring` (déjà public via F29) — un lien discret « Méthodologie » est présent dans le footer de la page.
- **P2 RLS** : routes consommées (`GET /me/credit-score`, `POST /me/credit-score/recompute`, `POST /me/credit-data`, `GET /me/credit-score/history`, `GET /me/credit-score/eligibility`, `GET /me/credit-score/recommendations`) appliquent toutes RLS via `account_id` dérivé du JWT (`Depends(get_current_pme)` déjà câblé). Cross-tenant → 404 testé pour chaque nouveau endpoint.
- **P3 Audit** : la page n'introduit aucune mutation directe : édition `credit_data` = écriture déjà tracée par F29 (`submit_credit_data` → audit), recalcul = écriture déjà tracée par F29 (`recompute_score` → audit). Les trois nouveaux endpoints sont en lecture pure → pas d'audit. **FR-019** est satisfait par les chemins F29 existants.
- **P4 Versioning** : la version méthodologie utilisée (`methodologie_version` de `CreditScoreOut`) est affichée dans l'historique au survol et dans le footer. Le catalogue d'éligibilité porte `version` + `valid_from` + `valid_to` ; un changement de catalogue ne réécrit jamais les anciens scores. Le wizard empty-state stocke ses réponses partielles en `localStorage` mais ne crée aucune ligne tant que la dernière étape n'est pas validée (donc pas de problème de versioning sur des données non publiées).
- **P5 Money typé** : tous les champs financiers (CA, EBE, dette, fonds propres) saisis dans le bottom sheet sont typés `{amount: Decimal, currency: ISO 4217}` côté UI via `<UiNumber money>` (F37) backed par `decimal.js`. L'envoi se fait au format `Money` standard du projet (le `payload` de `POST /me/credit-data` accepte du JSON libre par `dict[str, Any]`, mais le contrat F48 exige des objets `Money` typés — voir `contracts/frontend-api-consumption.md`).
- **P6 Pivot Indicateur unique** : la page ne stocke aucun indicateur ESG en propre — elle agrège seulement les `facteurs` retournés par F29 et affiche les sous-scores comme **vues dérivées**. Aucune duplication par axe ni par référentiel.
- **P7 Plateforme fermée aux intermédiaires** : aucun rôle banque/fonds. Le clic sur badge BOAD-vert ouvre une modal informative + lien vers le matching d'offres (F53, hors-scope F48) ; aucun envoi automatique vers BOAD/SUNREF. Le rapport export (US10, P2) est un fichier téléchargeable par la PME — partage signé Ed25519 reste hors-scope (couvert par F30 attestation).
- **P8 Édition manuelle + sync LLM** : tous les champs alimentés par le LLM (notamment via le chat) sont modifiables manuellement via le bottom sheet du `/credit-score`. Toute modification manuelle invalide immédiatement le contexte LLM en émettant `entity_updated{credit_data, credit_score}` sur le bus. Inversement, toute mutation LLM côté chat invalide le store côté UI. La DB reste source de vérité.
- **P9 Tool-use LLM fiable** : aucun nouveau tool LLM. Les tools existants côté F29/F41 (`submit_credit_data`, `recompute_credit_score`) émettent déjà les events consommés ici. Pas d'eval gating à introduire pour cette feature.
- **P10 UX bottom sheet** : la **seule** saisie utilisateur libre (édition des montants financiers + wizard 4 étapes) vit dans `<ChatBottomSheet>` + `<ShowForm ask_form>` (F39). Les modals d'éligibilité (`<UiModal>`) ne contiennent **aucun input** — uniquement texte + boutons (lien matching, fermer). Le bouton « Répondre librement » du `<ChatBottomSheet>` reste accessible pour basculer sur saisie libre dans le chat si la PME préfère.

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ✓ (existant inchangé).
- Dev local : backend `.venv`, Postgres seul service Docker, frontend `pnpm dev` ✓.
- Hébergement production : Europe ou Afrique de l'Ouest uniquement ✓.
- Conformité : RGPD + UEMOA 20/2010 + loi ivoirienne 2013-450 — données financières considérées comme données personnelles d'entreprise (pas physiques) ; rétention héritée de F29 (audit conservé selon politique projet).
- Langue : français par défaut ✓ (clés ajoutées dans `frontend/app/locales/fr.ts` sous le namespace `credit_score.*`).

**Scale/Scope** : 1 page nouvelle + ~15 composants nouveaux + 1 store + 5 composables + 3 helpers + 3 endpoints backend + 1 extension de schéma. ~1500–1800 LOC frontend nouvelles + ~250 LOC backend nouvelles + ~200 LOC tests backend. Volume utilisateur : MVP — quelques centaines de PME pendant la phase pilote, ~1 score par PME, jusqu'à ~10 dispositifs d'éligibilité par catalogue, jusqu'à ~24 calculs historiques par PME.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Le catalogue d'éligibilité (3+ dispositifs) déclare un `source_id` `verified` par dispositif. Les facteurs de score héritent du `source_id` de F29. La méthodologie est consultable. Le bandeau « Couverture partielle » explicite ce qui manque. La modal d'éligibilité expose les critères avec leur source. | ✅ |
| P2 | Multi-tenant RLS | Routes consommées passent par `Depends(get_current_pme)` ; les 3 nouveaux endpoints (`/history`, `/eligibility`, `/recommendations`) filtrent SQL par `account_id` (validé par tests cross-tenant → 404 ou liste vide selon endpoint). Aucun accès direct DB côté front. | ✅ |
| P3 | Audit log append-only | Aucune nouvelle mutation directe : édition `credit_data` et recalcul restent sur les chemins F29 audités. Les 3 nouveaux endpoints sont read-only → exemptés d'audit. FR-019 satisfait par F29. | ✅ |
| P4 | Versioning + snapshot candidatures | Pas de candidature ici. Les `credit_score` portent déjà `methodologie_version` (F29). Le catalogue d'éligibilité porte `version` + `valid_from` + `valid_to` côté module Python — un changement de règles d'éligibilité ne réécrit jamais les anciens scores. | ✅ |
| P5 | Money typé | Saisies CA/EBE/dette/fonds propres typées `Money = {amount: Decimal, currency}` via `<UiNumber money>` + `decimal.js` côté UI ; sérialisation `Money` dans le payload `POST /me/credit-data`. Pas de `float` côté UI. | ✅ |
| P6 | Pivot Indicateur unique | La page agrège uniquement les `facteurs` de `CreditScoreOut`. Les 4 sous-scores sont des vues dérivées, pas un nouveau stockage. Aucun nouvel `Indicateur`. | ✅ |
| P7 | Plateforme fermée aux intermédiaires | Aucun rôle banque/fonds. Lien badge → matching F53 (interne PME). Aucun envoi automatique vers BOAD/SUNREF/Ecobank. Export PDF (P2) reste un téléchargement local. | ✅ |
| P8 | Édition manuelle + sync LLM | Tous les champs LLM-alimentables sont modifiables manuellement via le bottom sheet. Toute mutation locale émet `entity_updated{credit_data, credit_score}`. Toute mutation chat invalide le store via `useChatEventBus`. DB = vérité. | ✅ |
| P9 | Tool-use LLM fiable | Aucun nouveau tool. Tools existants F29/F41 (`submit_credit_data`, `recompute_credit_score`) déjà sous schéma strict. Eval gating non requis pour cette feature. | ✅ N/A |
| P10 | UX bottom sheet | Saisies financières + wizard 4 étapes vivent dans `<ChatBottomSheet>` + `<ShowForm ask_form>`. Modal éligibilité = texte + lien (pas d'input). Bouton « Répondre librement » dispo dans `<ChatBottomSheet>`. | ✅ |

Aucun gate ❌. Pas de Complexity Tracking nécessaire.

## Project Structure

### Documentation (this feature)

```text
specs/048-credit-scoring-ui/
├── plan.md              # Ce fichier
├── research.md          # Phase 0 — décisions techniques (mapping sous-scores, catalogue éligibilité, F45 contrat recommandations, gauge component, classification thresholds)
├── data-model.md        # Phase 1 — ViewModels UI dérivés de CreditScoreOut + EligibilityBadgeOut + ScoreHistoryEntry + CreditRecommendationOut
├── quickstart.md        # Phase 1 — comment tester localement de bout en bout
├── contracts/
│   ├── backend-history-endpoint.md         # Contrat OpenAPI GET /me/credit-score/history
│   ├── backend-eligibility-endpoint.md     # Contrat OpenAPI GET /me/credit-score/eligibility + schéma catalogue
│   ├── backend-recommendations-endpoint.md # Contrat OpenAPI GET /me/credit-score/recommendations + dépendance F45
│   ├── backend-subscores-extension.md      # Contrat extension CreditScoreOut.subscores (mapping facteur→bucket)
│   ├── frontend-api-consumption.md         # Contrats des endpoints F29 + F45 + F48 consommés (entrées/sorties UI)
│   ├── frontend-components.md              # Contrats des composants/composables/helpers nouveaux
│   └── chat-eventbus-sync.md               # Contrat d'évènements chat ↔ credit-score (invalidations ciblées)
├── checklists/
│   └── requirements.md                     # Spec quality checklist (déjà créée)
└── tasks.md             # Phase 2 — généré par /speckit-tasks (PAS par /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   └── credit/
│       ├── router.py                   # MODIFIE — ajout 3 routes (history, eligibility, recommendations) (~80 LOC)
│       ├── service.py                  # MODIFIE — ajout list_history(), evaluate_eligibility(), list_recommendations() ; extension recompute_score()/get_latest_score() pour calculer subscores (~120 LOC)
│       ├── schemas.py                  # MODIFIE — ajout ScoreHistoryEntry, ScoreHistoryOut, EligibilityBadgeOut, EligibilityListOut, CreditRecommendationOut, CreditRecommendationsOut ; extension CreditScoreOut.subscores (Pydantic v2 strict) (~50 LOC)
│       ├── eligibility_catalog.py      # NEW — catalogue déclaratif versionné des dispositifs (BOAD-vert, SUNREF, Ecobank-Green-Lending) avec règles + source_id + version (~150 LOC pour 3 dispositifs)
│       └── subscore_mapping.py         # NEW — table de correspondance factor_name → bucket sous-score (4 buckets) (~50 LOC)
└── tests/
    └── credit/
        ├── test_history_endpoint.py            # NEW
        ├── test_eligibility_endpoint.py        # NEW
        ├── test_recommendations_endpoint.py    # NEW
        └── test_subscores_extension.py         # NEW

frontend/
├── app/
│   ├── pages/
│   │   └── credit-score/
│   │       └── index.vue                       # NEW — entry point
│   ├── components/
│   │   └── credit-score/                       # NEW — famille credit-score
│   │       ├── GaugeHero.vue                   # gauge gsap 0-100 + classification + delta N-1
│   │       ├── ClassificationLabel.vue         # libellé + couleur + texte alternatif daltonien
│   │       ├── PartialCoverageBanner.vue       # bandeau "Couverture partielle"
│   │       ├── SubScoreCard.vue                # carte sous-score (×4)
│   │       ├── SubScoreGrid.vue                # layout 2×2 / pile mobile
│   │       ├── EligibilityBadge.vue            # badge avec raison principale uniquement
│   │       ├── EligibilityDetailModal.vue      # modal détail critères + lien matching
│   │       ├── RecommendationList.vue          # 3-5 cartes
│   │       ├── RecommendationCard.vue          # action + impact estimé
│   │       ├── CreditDataDrawer.vue            # orchestre bottom sheet 4 étapes financières
│   │       ├── RecalcStrip.vue                 # horodatage + bouton recalc + spinner
│   │       ├── ScoreHistoryChart.vue           # <VizLineChart> 6 derniers calculs
│   │       ├── EmptyStateWizard.vue            # wizard 4 étapes via <ChatBottomSheet>
│   │       └── ExportPdfButton.vue             # P2 — désactivé MVP
│   ├── composables/
│   │   ├── useCreditScore.ts                   # NEW
│   │   ├── useCreditEligibility.ts             # NEW
│   │   ├── useCreditHistory.ts                 # NEW
│   │   ├── useCreditEdit.ts                    # NEW
│   │   ├── useCreditWizard.ts                  # NEW
│   │   ├── useChatEventBus.ts                  # EXISTANT (F41)
│   │   ├── useChatBottomSheet.ts               # EXISTANT (F39)
│   │   ├── useT.ts                             # EXISTANT
│   │   ├── useReducedMotion.ts                 # EXISTANT
│   │   ├── useChartTheme.ts                    # EXISTANT
│   │   ├── useDecimal.ts                       # EXISTANT
│   │   ├── useMoneyFormat.ts                   # EXISTANT
│   │   └── useToast.ts                         # EXISTANT
│   ├── stores/
│   │   └── creditScore.ts                      # NEW — score, sous-scores, éligibilité, historique, mode wizard
│   ├── lib/
│   │   ├── classifyCreditScore.ts              # NEW — seuils 80/60/40 (clarification Q2)
│   │   ├── selectCreditRecommendations.ts      # NEW — filet de tri/filtre côté client (clarification Q1)
│   │   └── animateGaugeTransition.ts           # NEW — tween gsap 320 ms respectant reduced-motion
│   ├── locales/
│   │   └── fr.ts                               # MODIFIE — namespace credit_score.*
│   └── assets/css/main.css                     # éventuelles classes utilitaires
└── tests/
    ├── unit/
    │   ├── composables/
    │   │   ├── useCreditScore.test.ts
    │   │   ├── useCreditEligibility.test.ts
    │   │   ├── useCreditHistory.test.ts
    │   │   ├── useCreditEdit.test.ts
    │   │   └── useCreditWizard.test.ts
    │   ├── stores/
    │   │   └── creditScore.test.ts
    │   └── lib/
    │       ├── classifyCreditScore.test.ts
    │       ├── selectCreditRecommendations.test.ts
    │       └── animateGaugeTransition.test.ts
    ├── components/
    │   └── credit-score/
    │       ├── GaugeHero.test.ts
    │       ├── ClassificationLabel.test.ts
    │       ├── PartialCoverageBanner.test.ts
    │       ├── SubScoreCard.test.ts
    │       ├── SubScoreGrid.test.ts
    │       ├── EligibilityBadge.test.ts
    │       ├── EligibilityDetailModal.test.ts
    │       ├── RecommendationList.test.ts
    │       ├── RecommendationCard.test.ts
    │       ├── CreditDataDrawer.test.ts
    │       ├── RecalcStrip.test.ts
    │       ├── ScoreHistoryChart.test.ts
    │       ├── EmptyStateWizard.test.ts
    │       └── ExportPdfButton.test.ts
    └── e2e/
        ├── credit-score-overview-render.spec.ts
        ├── credit-score-classification-thresholds.spec.ts
        ├── credit-score-subscores-render.spec.ts
        ├── credit-score-eligibility-badges.spec.ts
        ├── credit-score-eligibility-modal.spec.ts
        ├── credit-score-recommendations-flow.spec.ts
        ├── credit-score-edit-data-flow.spec.ts
        ├── credit-score-edit-money-validation.spec.ts
        ├── credit-score-recalc-failure.spec.ts
        ├── credit-score-history-render.spec.ts
        ├── credit-score-empty-state-wizard.spec.ts
        ├── credit-score-partial-coverage.spec.ts
        ├── credit-score-chat-sync.spec.ts
        ├── credit-score-color-blind-friendly.spec.ts
        ├── credit-score-reduced-motion.spec.ts
        └── credit-score-recommendation-deadlink.spec.ts
```

**Structure Decision** : Application web mono-repo Nuxt 4 + FastAPI déjà en place. Cette feature touche principalement `frontend/app/` ; côté backend, 3 fichiers F29 existants sont modifiés de façon additive (router, service, schemas) plus 2 fichiers nouveaux (`eligibility_catalog.py` déclaratif, `subscore_mapping.py` déclaratif) plus 4 fichiers de tests. Le découpage `components/credit-score/*` reflète la frontière de domaine UI sans empiéter sur `components/scoring/*` (F46), `components/dashboard/*` (F44), `components/plan-action/*` (F45) ou `components/carbone/*` (F47). Le store `creditScore.ts` est partagé : la mini-card crédit du `/dashboard` (F44, si déjà livrée) sera **modifiée** pour lire ce store, garantissant cohérence et invalidation unique. Les tests sont structurés en `unit/` (composables, store, lib), `components/` (composants Vue), `e2e/` (Playwright) — héritage F38/F42/F43/F44/F45/F46/F47.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Aucune violation. Tableau vide.
