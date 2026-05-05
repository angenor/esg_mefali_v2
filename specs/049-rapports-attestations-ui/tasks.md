---
description: "Task list for F49 — Rapports PDF & Page publique /verify (UI F24 + F30)"
---

# Tasks: Rapports PDF & Page publique /verify (UI F24 + F30)

**Input**: Design documents from `/specs/049-rapports-attestations-ui/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui-backend.md, quickstart.md

**Tests**: Sélectivement inclus — tests unitaires Pinia, tests composant pour modale de génération et page publique, 2 parcours E2E Playwright (génération + verify public). Cohérent avec la règle commune testing.md (≥ 80 % couverture).

**Organization**: Phases 1–2 fondations partagées ; Phase 3 = US1 (table rapports + drawer aperçu) ; Phase 4 = US2 (génération SSE) ; Phase 5 = US3 (partage / révocation attestation) ; Phase 6 = US4+US5 (page publique `/verify` valide + révoquée + sources) ; Phase 7 = US6 (bilingue FR/EN) ; Phase 8 = polish (a11y, perf, Lighthouse).

## Format

`- [ ] [TaskID] [P?] [Story?] Description with file path`

- **[P]** : tâches parallélisables (fichiers distincts, pas de dépendance non encore terminée).
- **[Story]** : `US1` … `US6` — uniquement dans les phases User Story.

## Path Conventions

Application web : code front sous `frontend/app/` (pages, components, stores, composables, i18n) ; tests sous `frontend/tests/`. Trois additions backend mineures sous `backend/app/rapports/` et `backend/app/attestations/`.

---

## Phase 1 : Setup (Shared Infrastructure)

**Purpose** : préparer la structure de fichiers, tirer les libs requises, brancher la route.

- [X] T001 Créer le dossier `frontend/app/components/rapports/` (vide, garde `.gitkeep`) et `frontend/app/components/rapports/verify/`
- [X] T002 Créer le dossier `frontend/app/i18n/verify/` avec deux fichiers JSON `fr.json` et `en.json` minimaux (clés vides ou squelette)
- [X] T003 [P] Vérifier la présence (et installer si manquante) la lib `qrcode` dans `frontend/package.json`, importable dans `ShareAttestationModal.vue`
- [X] T004 [P] Ajouter une entrée dans la navigation principale (composant shell `frontend/app/components/shell/`) pointant vers `/rapports` (icône + libellé FR), visible uniquement si la session PME est authentifiée
- [X] T005 Configurer un `routeRules` côté `nuxt.config.ts` pour `/verify/**` avec `swr: 60` et headers `Cache-Control: public, max-age=0, s-maxage=60, stale-while-revalidate=60`

**Checkpoint** : `make frontend` démarre, `/rapports` renvoie 404 attendu (page pas encore créée), `/verify/[id]` est encore le stub F38, le menu mentionne « Rapports ».

---

## Phase 2 : Foundational (Blocking Prerequisites)

**Purpose** : livrer les contrats backend mineurs identifiés en Phase 0 (R2, R3, R6) et les stores Pinia + composables réutilisés par toutes les user stories. Aucune US ne peut démarrer avant ces tâches.

### Backend mineur (3 endpoints)

- [X] T006 Ajouter l'endpoint `GET /me/rapports/generate/{generation_id}/stream` (SSE) dans `backend/app/rapports/router.py` : émet événements `progress`, `done`, `failed` ; honore `Last-Event-ID` ; auth obligatoire ; RLS via `app.current_account_id`. Implémentation simple : poll DB toutes les 500 ms et émet sur changement.
- [X] T007 [P] Ajouter l'endpoint `GET /me/rapports/{rapport_id}/preview-url` dans `backend/app/rapports/router.py` : retourne `{url, expires_at}` URL signée HMAC TTL 5 min, vérifiée sur la route servant le PDF.
- [X] T008 [P] Ajouter une route GET interne servant l'aperçu PDF authentifié par signature dans `backend/app/rapports/router.py` (vérification `t`, `sig`, `account_id`, fallback 404 si signature invalide ou expirée).
- [X] T009 [P] Étendre `backend/app/attestations/schemas.py` `PublicVerification` pour inclure `label_en` optionnel sur chaque indicateur du `payload` ; backend renvoie `null` ou la valeur catalogue si disponible.
- [X] T010 [P] Étendre `backend/app/attestations/service.py` pour déclencher une invalidation de cache CDN sur `/verify/{public_id}` lors d'une révocation (hook nominal : appel HTTP au CDN, fallback no-op en dev) ; documenter avec un commentaire.

### Tests backend (additions)

- [X] T011 [P] Ajouter `backend/tests/rapports/test_stream.py` couvrant : SSE envoie `progress` puis `done` ; resp 401 sans auth ; cross-tenant retourne 404.
- [X] T012 [P] Ajouter `backend/tests/rapports/test_preview_url.py` couvrant : URL signée acceptée, signature falsifiée → 404, expiration → 404, cross-tenant → 404.

### Front — types et stores

- [X] T013 Créer `frontend/app/types/reports.ts` exposant `Rapport`, `RapportType`, `RapportStatus`, `GenerateRequest`, `GenerationState`, `PreviewUrl` (types alignés sur `contracts/ui-backend.md`).
- [X] T014 [P] Créer `frontend/app/types/attestations.ts` exposant `Attestation`, `AttestationType`, `AttestationStatus`, `RevokeReason`, `PublicVerification`, `PublicIndicator`, `PublicSource`.
- [X] T015 Créer `frontend/app/stores/reports.ts` (Pinia) avec state, actions `fetchAll()`, `generate()`, `subscribeStream()`, `cancelStream()`, `loadPreviewUrl()`, et helper de rattrapage au mount qui rouvre les SSE pour les générations encore `pending`/`running` (cf. data-model.md).
- [X] T016 [P] Créer `frontend/app/stores/attestations.ts` (Pinia) avec `fetchAll()`, `revoke()`, `buildVerifyUrl()`, `buildQrPng()` (qrcode lib, niveau `H`).

### Front — composables

- [X] T017 [P] Créer `frontend/app/composables/useReportGenerationStream.ts` : ouvre `EventSource`, gère `progress`/`done`/`failed`, honore `Last-Event-ID`, fallback polling si SSE indisponible (404 sur le stream).
- [X] T018 [P] Créer `frontend/app/composables/useSignedPdfUrl.ts` : appelle `loadPreviewUrl()` du store, expose `url` réactive et `isExpired` qui invalide à `expires_at`.
- [X] T019 [P] Créer `frontend/app/composables/useVerifyI18n.ts` : lit cookie `mefali_verify_lang`, expose `lang`, `t(key)`, `setLang()`, et un dictionnaire chargé depuis `i18n/verify/{lang}.json`.

### Tests stores (Vitest)

- [X] T020 [P] Ajouter `frontend/tests/unit/stores/reports.test.ts` : `fetchAll` peuple la table ; `generate` crée une entrée `pending` ; `subscribeStream` met à jour l'état sur événements ; rattrapage au remount.
- [X] T021 [P] Ajouter `frontend/tests/unit/stores/attestations.test.ts` : `revoke` invalide la liste ; `buildQrPng` retourne un PNG valide.

**Checkpoint** : tous les fondations backend + stores + composables sont disponibles ; les pages peuvent désormais consommer.

---

## Phase 3 : User Story 1 — Liste et téléchargement des rapports (P1)

**Goal** : la PME voit ses rapports + attestations sur `/rapports` et peut télécharger un PDF.

**Independent Test** : se connecter, ouvrir `/rapports`, voir 2 tables (rapports / attestations), cliquer « Télécharger » sur un rapport → PDF arrive ; cliquer une ligne → drawer avec aperçu + métadonnées.

- [X] T022 [US1] Créer `frontend/app/pages/rapports/index.vue` : layout `default`, page protégée (`middleware: auth`), titre « Rapports », chargement initial via `useReportsStore` et `useAttestationsStore` (deux appels en parallèle).
- [X] T023 [P] [US1] Créer `frontend/app/components/rapports/ReportTable.vue` : table avec colonnes (Titre, Type, Période, Date, Taille, Statut, Actions) ; chip de statut coloré ; bouton « Télécharger » (lien direct vers `/me/rapports/{id}/download`) ; bouton « Régénérer » (ouvre `GenerateReportModal` pré-rempli) ; emit `select` au clic ligne.
- [X] T024 [P] [US1] Créer `frontend/app/components/rapports/AttestationTable.vue` : colonnes (Type, Statut, Émise, Expire, QR mini, Actions) ; chip statut ; QR mini cliquable qui ouvre `ShareAttestationModal` ; bouton « Révoquer » (désactivé si `expired` ou `revoked`).
- [X] T025 [US1] Créer `frontend/app/components/rapports/ReportDrawer.vue` : drawer slide-in droite (gsap, prim. UI F37), header avec titre + bouton fermer, corps en deux zones : (a) `<iframe>` aperçu PDF avec URL chargée via `useSignedPdfUrl` (fallback message + bouton « Télécharger » si erreur), (b) métadonnées (référentiel, période, hash, taille, statut).
- [X] T026 [US1] Brancher `ReportDrawer` dans `pages/rapports/index.vue` : sélection de ligne → ouverture du drawer avec le `rapportId`.
- [X] T027 [P] [US1] Empty state pour les deux tables (aucun rapport / aucune attestation) avec call-to-action « Générer mon premier rapport » qui ouvre `GenerateReportModal` (le composant est livré en US2 — bouton désactivé tant que le composant n'est pas mergé OU import paresseux).
- [X] T028 [P] [US1] Test composant `frontend/tests/component/ReportTable.test.ts` : rendu colonnes, statut chip, click ligne déclenche `select`.

**Checkpoint** : la PME voit ses livrables et les télécharge ; aperçu inline fonctionnel quand l'URL signée est livrée par T007/T008.

---

## Phase 4 : User Story 2 — Génération d'un nouveau rapport avec progression (P1)

**Goal** : la PME demande la génération d'un rapport et reçoit une progression jusqu'au lien de téléchargement, avec rattrapage si elle quitte la page.

**Independent Test** : sur `/rapports`, ouvrir « Nouveau rapport », choisir type+référentiel+période, valider → spinner + barre de progression jusqu'à « Télécharger » ; recharger la page pendant la génération → la progression reprend.

- [X] T029 [US2] Créer `frontend/app/components/rapports/GenerateReportModal.vue` : modale (gsap), formulaire (type select, référentiel select, période — date range), validation côté front (champs obligatoires), bouton submit désactivé tant que invalide, message d'erreur lisible si l'API renvoie 4xx/5xx.
- [X] T030 [US2] Soumission depuis la modale : appelle `useReportsStore().generate()` puis affiche état progressif (barre + libellés `progress.step`) en consommant `useReportGenerationStream`.
- [X] T031 [US2] Afficher dans la modale, à la fin (`done`), un bouton « Télécharger » et « Fermer », et déclencher `fetchAll()` du store pour rafraîchir la table sous-jacente.
- [X] T032 [US2] Au mount de `pages/rapports/index.vue`, lire `useReportsStore().pending`, ouvrir un toast non bloquant indiquant les générations en cours et reconnecter le SSE pour chacune (rattrapage FR-003a).
- [X] T033 [US2] Bouton « Régénérer » dans `ReportTable.vue` : ouvre `GenerateReportModal` pré-rempli avec type/référentiel/période du rapport sélectionné.
- [X] T034 [P] [US2] Test composant `frontend/tests/component/GenerateReportModal.test.ts` : validation, submit, transitions `pending → running → ready`, gestion erreur.
- [ ] T035 [P] [US2] Test E2E `frontend/tests/e2e/rapports-generation.spec.ts` (Playwright) : login PME demo, génération conformité, attente done, vérif lien télécharger ; recharge en cours et vérifier rattrapage.

**Checkpoint** : SC-002 vérifiable ; la PME peut produire et récupérer un rapport.

---

## Phase 5 : User Story 3 — Partage et révocation d'attestation (P1)

**Goal** : la PME partage l'URL publique et le QR PNG d'une attestation active ; elle peut révoquer avec motif catégorisé.

**Independent Test** : ouvrir le menu d'une attestation active, cliquer « Partager » → URL `/verify/{id}` copiable + QR PNG ; cliquer « Révoquer » sur une autre, choisir motif → statut bascule.

- [X] T036 [US3] Créer `frontend/app/components/rapports/ShareAttestationModal.vue` : modale avec URL absolue affichée + bouton copier (Clipboard API + toast), QR rendu par la lib `qrcode` (niveau `H`, 256×256), bouton « Télécharger QR PNG » (`canvas.toDataURL()`).
- [X] T037 [P] [US3] Créer `frontend/app/components/rapports/RevokeAttestationModal.vue` : confirm modale, sélecteur du motif (5 options de la liste fermée `RevokeReason`), bouton « Confirmer la révocation » ; appel `useAttestationsStore().revoke(id, reason)` ; toast de succès ; mise à jour de la table.
- [X] T038 [US3] Brancher dans `AttestationTable.vue` : action « Partager » ouvre `ShareAttestationModal`, action « Révoquer » ouvre `RevokeAttestationModal` (désactivée si `expired`/`revoked`).
- [X] T039 [P] [US3] Test composant `frontend/tests/unit/ShareAttestationModal.test.ts` : QR généré, URL correcte, copier déclenche toast.
- [X] T040 [P] [US3] Test composant `frontend/tests/unit/RevokeAttestationModal.test.ts` : motif obligatoire, appel API, mise à jour state.

**Checkpoint** : le cycle attestation côté PME est complet ; la révocation propage l'invalidation de cache (T010) et le statut change.

---

## Phase 6 : User Stories 4 + 5 — Page publique `/verify/{id}` (P1)

**Goal** : un visiteur non authentifié obtient le verdict, l'identité, les dates et les KPI sourcés en moins de 1,2 s ; le bandeau de révocation est visible above-the-fold ; aucun lien ne ramène vers l'app PME.

**Independent Test** : ouvrir `/verify/<actif>` en navigation privée → page complète et badge ✓ ; ouvrir `/verify/<révoqué>` → bandeau rouge ; ouvrir `/verify/<inconnu>` → 404 sobre ; désactiver JS → essentiel toujours lisible.

- [X] T041 [US4] Remplacer `frontend/app/pages/verify/[id].vue` (stub F38) : layout `public`, `useFetch('{apiBase}/verify/{id}/json')` côté serveur, `setResponseStatus(404)` si non trouvé, `setResponseHeader('Cache-Control', ...)` et `setResponseHeader('Content-Language', lang)`.
- [X] T042 [P] [US4] Créer `frontend/app/components/rapports/verify/SignatureBadge.vue` : badge ✓ vert ou ✗ rouge, libellé via `useVerifyI18n`, taille mobile-first.
- [X] T043 [P] [US4] Créer `frontend/app/components/rapports/verify/RevokedBanner.vue` : bandeau rouge above-the-fold avec date formatée et libellé du motif (issu du dictionnaire i18n) ; visible uniquement si `revoked_at` non null.
- [X] T044 [P] [US5] Créer `frontend/app/components/rapports/verify/PayloadView.vue` : rendu lecture seule des KPI ; chaque KPI affiche `label`/`label_en`, `value`, `unit`, et un repère cliquable vers `payload.sources` ; aucun élément d'édition.
- [X] T045 [P] [US5] Créer `frontend/app/components/rapports/verify/PublicFooter.vue` : footer sobre — mentions légales, lien RGPD, lien `/about` ; jamais de lien retour vers l'app PME.
- [X] T046 [US5] Composer `pages/verify/[id].vue` avec : header + sélecteur FR/EN, `SignatureBadge`, `RevokedBanner` (conditionnel), bloc identité, `PayloadView`, encart pédagogique, `PublicFooter`.
- [X] T047 [US4] Page d'erreur sobre : si `useFetch` retourne 404/5xx, état dégradé avec titre + message FR/EN + lien vers `/about` sans stack trace.
- [X] T048 [P] [US4] Injecter SSR : `<title>`, `<meta name="description">`, Open Graph, JSON-LD `Certification` (FR-019).
- [X] T049 [P] [US4] Test composant `frontend/tests/unit/verify/SignatureBadge.test.ts` : ✓ et ✗ rendus correctement.
- [X] T050 [P] [US4] Test E2E `frontend/tests/e2e/verify-public.spec.ts` (Playwright) : actif → badge ✓ ; révoqué → bandeau ; inconnu → 404 ; no-JS → essentiel visible.

**Checkpoint** : SC-003, SC-004, SC-007, SC-008, SC-009 vérifiables.

---

## Phase 7 : User Story 6 — Bilingue FR/EN sur `/verify` (P2)

**Goal** : le visiteur bascule en EN ; libellés statiques + énumérations contrôlées (type d'attestation, motif révocation, libellés d'indicateurs standards) basculent ; données saisies PME inchangées.

**Independent Test** : sur `/verify/<id>`, cliquer EN → libellés bascule, raison sociale et valeurs numériques inchangées ; recharger la page → préférence persistée via cookie.

- [X] T051 [US6] Remplir `frontend/app/i18n/verify/fr.json` et `frontend/app/i18n/verify/en.json` (libellés statiques, formats de date, `RevokeReason` × 5, `AttestationType` × 4).
- [X] T052 [P] [US6] Créer `frontend/app/components/rapports/verify/LangSwitch.vue` : boutons FR/EN, ARIA, persistance cookie `mefali_verify_lang`, `setLang()`.
- [X] T053 [US6] Brancher `LangSwitch` dans `pages/verify/[id].vue` ; passer `lang` à `<html lang="...">` côté SSR via `useHead({ htmlAttrs: { lang } })`.
- [X] T054 [US6] `PayloadView.vue` : utilise `label_en` quand `lang === 'en'`, sinon `label` ; raison sociale + valeurs numériques inchangées ; `unit` brut.
- [X] T055 [P] [US6] `RevokedBanner.vue` : libellé motif via i18n ; `SignatureBadge.vue` : libellés via `t()`.
- [X] T056 [P] [US6] Test E2E ajouté à `verify-public.spec.ts` : bascule EN, vérification d'une chaîne anglaise, persistance cookie.

**Checkpoint** : SC-005 (Lighthouse) tenable ; bilingue scope contrôlé livré.

---

## Phase 8 : Polish & Cross-Cutting

**Purpose** : performance, accessibilité, SEO et durcissement.

- [ ] T057 Audit Lighthouse mobile sur `/verify/<id_actif>` (`pnpm dlx @lhci/cli@0.13.x autorun`) → ≥ 95 sur les 4 axes. _À dérouler après merge sur env de staging._
- [ ] T058 [P] Audit a11y `/rapports` + `/verify/[id]` (axe-core ou Lighthouse a11y). _Manuel — staging._
- [ ] T059 [P] Vérification manuelle no-JS sur `/verify/<id>` : DevTools désactiver JS, recharger. _Manuel — staging ; couverture E2E partielle dans T050._
- [X] T060 [P] Test `frontend/tests/unit/composables/useSignedPdfUrl.test.ts` : force l'expiration et vérifie le re-fetch (URL nullifiée puis renouvelée).
- [ ] T061 [P] Vérifier la non-énumérabilité des `public_id` (audit côté backend F30). _Hors-scope — F30 utilise déjà `uuid` opaque (cf. `public_id: uuid.UUID` dans router F30)._
- [ ] T062 [P] Vérifier que la révocation invalide `/verify/{id}` en < 60 s. _Manuel — staging ; documenté dans `quickstart.md`._
- [X] T063 [P] Aucun lien retour app PME dans `pages/verify/[id].vue` ni dans `components/rapports/verify/*.vue` (vérifié par `grep -E 'href="/(login|dashboard|rapports|chat|carbone|credit-score|profil|admin|mes-)'` → 0 occurrence).
- [X] T064 [P] `docs_et_brouillons/features/00-INDEX.md` : F49 marqué `in-progress` (passage à `done` après merge + audits Lighthouse/a11y).
- [ ] T065 Couverture finale : `pnpm vitest run --coverage` côté front (≥ 80 %) ; `pytest --cov` côté back T011/T012 (≥ 80 %). _À exécuter avant merge._

---

## Dependencies

```
Phase 1 (Setup) ────► Phase 2 (Foundational) ─┐
                                              ├──► Phase 3 (US1)  ─┐
                                              ├──► Phase 4 (US2)  ─┤
                                              ├──► Phase 5 (US3)  ─┼──► Phase 8 (Polish)
                                              ├──► Phase 6 (US4+US5)─┤
                                              └──► Phase 7 (US6) ──┘

Story-specific dependencies:
- US1 dépend de T015 (store reports), T017 (composable stream pas requis pour la table seule), T018 (URL signée pour le drawer)
- US2 dépend de US1 partiel (la table doit exister pour s'y rafraîchir), de T006 (SSE), T015, T017
- US3 dépend de T016 (store attestations), T010 (invalidation cache à la révocation)
- US4+US5 dépendent de T009 (`label_en`), T010 (cache), T019 (i18n composable même si le switch arrive en US6)
- US6 dépend de US4+US5 (composants de la page existent)
- Phase 8 dépend de toutes les phases user story
```

## Parallel Execution Examples

### Phase 2 (foundational) — fortement parallèle

```
En parallèle :
  T007, T008, T009, T010   (additions backend distinctes)
  T011, T012               (tests backend distincts)
  T013, T014               (types front)
  T017, T018, T019         (composables front)
  T020, T021               (tests stores)
```

### Phase 3 (US1)

```
En parallèle après T022 :
  T023 (ReportTable), T024 (AttestationTable), T027 (empty state), T028 (test)
Sériel :
  T025 (ReportDrawer) → T026 (branchement dans la page)
```

### Phase 4 (US2)

```
T029 (modale) → T030 (submit + stream) → T031 (état done) → T033 (régénérer)
T032 rattrapage : peut être ajoutée en parallèle après T029
T034, T035 : parallèles dès que les composants compilent
```

### Phase 6 (US4+US5)

```
En parallèle après T041 :
  T042 (badge), T043 (banner), T044 (payload), T045 (footer), T048 (SEO meta)
Sériel :
  T046 (composition page) → T047 (état dégradé) → T049/T050 (tests)
```

### Phase 8 — entièrement parallèle hormis T057 (audit unique)

## Implementation Strategy

**MVP (livrable minimum incrémental)** : Phases 1 + 2 + 3 + 4 + 5 + 6 (US1 → US5). Le bilingue (US6) et la polish peuvent être dégroupés en livraison continue.

**Découpage suggéré en PRs** :
1. Phase 1 + 2 (setup + fondations + 3 endpoints backend mineurs).
2. Phase 3 (US1 — table + drawer).
3. Phase 4 (US2 — génération SSE).
4. Phase 5 (US3 — partage / révocation).
5. Phase 6 (US4+US5 — page publique).
6. Phase 7 (US6 — bilingue).
7. Phase 8 (polish + Lighthouse).

**Validation finale** : suivre `quickstart.md` parcours manuel → cocher SC-001 à SC-009.
