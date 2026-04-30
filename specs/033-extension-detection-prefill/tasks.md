# Tasks: F33 — Extension Chrome — Détection sites & pré-remplissage IA

**Branch**: `033-extension-detection-prefill`
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

## Phase 1 — Setup

- [ ] T001 Créer le module backend `backend/app/extension/__init__.py` (paquet vide)
- [ ] T002 Créer le dossier d'extension Chrome `extension/` à la racine du repo avec un README minimal `extension/README.md`

## Phase 2 — Foundational (prérequis bloquants)

- [ ] T003 Migration Alembic `backend/alembic/versions/f033_url_patterns_field_mapping.py` : tables `url_pattern` (id, pattern, pattern_type ENUM, nature ENUM, fonds_id, intermediaire_id, offre_id, is_active, preferred_language, created_at, updated_at) et `field_mapping_intermediaire` (id, intermediaire_id FK, mapping_json JSONB, created_at, updated_at) avec index sur (is_active) et (intermediaire_id)
- [ ] T004 Modèles SQLAlchemy `backend/app/models/url_pattern.py` (UrlPattern) et `backend/app/models/field_mapping_intermediaire.py` (FieldMappingIntermediaire), enregistrés dans `app/models/__init__.py`
- [ ] T005 Schemas Pydantic `backend/app/extension/schemas.py` : UrlPatternOut, UrlPatternListOut, ProfileSummaryOut, ProjetSummaryOut, SuggestFieldIn, SuggestFieldOut, FieldMappingOut, FieldMappingListOut, AdminUrlPatternIn, AdminUrlPatternUpdateIn
- [ ] T006 Service `backend/app/extension/url_matcher.py` : fonctions `match_wildcard(pattern, url)`, `match_regex(pattern, url)`, `compile_pattern(pattern, pattern_type)` — utilisé pour tests + validation côté admin
- [ ] T007 Service `backend/app/extension/service.py` : `list_active_url_patterns(db)`, `build_profile_summary(db, account_id, projet_id?)`, `suggest_field(db, user, payload)`, `list_field_mappings(db, intermediaire_id?)`
- [ ] T008 Configurer CORS pour `chrome-extension://*` dans `backend/app/main.py` (ajout origine, vérifier middleware existant)

## Phase 3 — US1 : Connecter l'extension (P1)

**Goal**: Permettre à la PME de se connecter via le popup, stocker JWT, afficher identité.
**Independent test**: Charger l'extension non-empaquetée, login dans popup, voir nom entreprise.

- [ ] T009 [P] [US1] Tests `backend/tests/extension/test_profile_summary.py` : 401 sans auth, 200 PME avec données minimales, ≤ 2 KB JSON, contient raison_sociale et secteur
- [ ] T010 [US1] Implémentation route `GET /extension/profile-summary` dans `backend/app/extension/router.py` (dependency `get_current_pme`, audit `extension.profile_summary`)
- [ ] T011 [P] [US1] `extension/manifest.json` : Manifest V3, action.default_popup, background.service_worker, content_scripts matches `<all_urls>`, permissions `storage`, `activeTab`, host_permissions configurables
- [ ] T012 [P] [US1] `extension/popup.html` + `extension/popup.css` : formulaire login email/password, zone affichage identité, bouton refresh patterns, sélecteur langue
- [ ] T013 [US1] `extension/popup.js` : POST vers `/auth/login` (URL backend depuis config), stocker `jwt` dans `chrome.storage.local`, GET `/extension/profile-summary` puis afficher identité
- [ ] T014 [P] [US1] `extension/_locales/fr/messages.json` et `extension/_locales/en/messages.json` : libellés popup (login, email, password, identity, refresh, language)

## Phase 4 — US2 : Détection automatique des sites (P1)

**Goal**: Bandeau d'Offre détectée sur sites fonds/intermédiaires.
**Independent test**: Activer un pattern admin, naviguer URL ciblée, voir bandeau.

- [ ] T015 [P] [US2] Tests `backend/tests/extension/test_url_matcher.py` : wildcard `*.boad.org/*` matche `https://www.boad.org/appels`, regex `^https://gcf\.org/funding/.*$`, non-match retourne False
- [ ] T016 [P] [US2] Tests `backend/tests/extension/test_url_patterns.py` : 401 sans auth, 200 retourne items[] uniquement actifs, exclut patterns sans Offre publiée
- [ ] T017 [US2] Implémentation route `GET /extension/url-patterns` dans `backend/app/extension/router.py` (dependency `get_current_pme`, audit `extension.view_patterns`)
- [ ] T018 [P] [US2] `extension/background.js` : service worker, fetch `/extension/url-patterns` au login + setInterval 1h, gestion 401 → broadcast `auth:expired`, refresh manuel via message `patterns:refresh`
- [ ] T019 [US2] `extension/content.js` (partie 1) : sur `DOMContentLoaded`, demander patterns au background, faire match URL courante, injecter bandeau (DIV overlay top, z-index élevé) avec libellé Offre + bouton dismiss

## Phase 5 — US3 : Observation SPA (P1)

**Goal**: Bandeau réagit aux changements de route SPA sans reload.
**Independent test**: Navigation `pushState`, bandeau s'adapte.

- [ ] T020 [US3] `extension/content.js` (partie 2) : hook `history.pushState` et `history.replaceState`, listener `popstate`, MutationObserver debounce 300 ms, ré-évaluer match et mettre à jour bandeau

## Phase 6 — US4 : Pré-remplissage avec code-couleur (P1)

**Goal**: Bouton "Tout remplir" mappe profil → champs avec code-couleur vert/bleu/orange.
**Independent test**: Form test, ≥ 70 % remplissage, code-couleur correct.

- [ ] T021 [P] [US4] Tests `backend/tests/extension/test_field_mappings.py` : GET `/extension/field-mappings` retourne mappings actifs, filtre par `intermediaire_id`
- [ ] T022 [US4] Implémentation route `GET /extension/field-mappings` dans `backend/app/extension/router.py` (dependency `get_current_pme`, audit `extension.field_mappings`)
- [ ] T023 [US4] Seed `backend/app/extension/seed_field_mappings.py` : insère mappings pour 2-3 intermédiaires (BOAD, SUNREF Ecobank, PNUD) avec dictionnaire label_pattern→profile_attr (raison_sociale, email, pays, montant_projet, description_projet)
- [ ] T024 [P] [US4] `extension/field_mapper.js` : fonctions `analyzeForm(form)`, `mapFieldToProfile(field, mappings, profileSummary)`, retourne `{element, value, source: 'profile'|'ai'|'none'}`
- [ ] T025 [US4] `extension/content.js` (partie 3) : injection bouton "Tout remplir" si formulaire détecté + match Offre, au clic appelle field_mapper, applique valeurs avec overlay coloré (vert/bleu/orange) sur chaque champ

## Phase 7 — US5 : Suggestion IA par champ (P1)

**Goal**: Bouton "Suggérer" sur champ texte, appelle backend, insère texte ≤ longueur max.
**Independent test**: Champ description, clic Suggérer, texte inséré < 3 s.

- [ ] T026 [P] [US5] Tests `backend/tests/extension/test_suggest_field.py` : 401 sans auth, 200 retourne text + length ≤ field_max_length, source 'llm' ou 'fallback', erreur LLM → fallback non-vide, audit log écrit
- [ ] T027 [US5] Implémentation route `POST /extension/suggest-field` dans `backend/app/extension/router.py` : appelle `service.suggest_field`, prompt court avec contexte projet/offre/intermédiaire, retry 1x sur erreur LLM, fallback `f"[Suggestion non disponible pour {field_label}]"`
- [ ] T028 [US5] `extension/content.js` (partie 4) : ajoute mini-bouton "Suggérer" à côté de chaque `<textarea>` ou `<input maxlength>` détecté sur sites matchés ; au clic POST `/extension/suggest-field` puis insère texte avec animation simple (opacity transition CSS)

## Phase 8 — US6 : i18n FR/EN (P1)

**Goal**: Interface bascule FR ↔ EN.
**Independent test**: Changer langue, libellés basculent.

- [ ] T029 [P] [US6] Compléter `extension/_locales/fr/messages.json` et `extension/_locales/en/messages.json` avec libellés bandeau, boutons content script, messages d'erreur, suggestion
- [ ] T030 [US6] `extension/popup.js` + `extension/content.js` : utiliser `chrome.i18n.getMessage(key)` pour tous les libellés ; persister préférence langue dans `chrome.storage.local`, détecter langue OS au premier lancement

## Phase 9 — US7 : Adaptation au format de l'intermédiaire (P1)

**Goal**: Suggestions adaptées au ton/format de l'intermédiaire détecté.
**Independent test**: Suggestions distinctes selon intermédiaire.

- [ ] T031 [US7] Étendre `service.suggest_field` : si `intermediaire_id` fourni, charger nom + description courte intermédiaire et l'inclure dans le prompt LLM (« Adapte le ton au format de [intermediaire.nom] »)

## Phase 10 — Admin : gestion des url_patterns (P1, transverse)

**Goal**: Admin CRUD patterns d'URL.
**Independent test**: Admin POST pattern, GET liste contient pattern.

- [ ] T032 [P] Tests `backend/tests/extension/test_admin_url_patterns.py` : 403 sans admin, POST création valide, validation pattern_type obligatoire, PATCH activation/désactivation, DELETE soft delete, GET paginé
- [ ] T033 Implémentation `backend/app/extension/admin_router.py` : routes `GET/POST/PATCH/DELETE /admin/url-patterns` avec `get_current_admin`, audit `extension.admin_pattern_{create|update|delete}`, validation pattern via `url_matcher.compile_pattern`
- [ ] T034 Brancher routers dans `backend/app/main.py` : `app.include_router(extension_router)` (PME) et `app.include_router(extension_admin_router)` (Admin)

## Phase 11 — Polish & Cross-Cutting

- [ ] T035 [P] Documentation `extension/README.md` : installation unpacked, configuration backend URL, login, troubleshooting CSP
- [ ] T036 [P] Manual test log `.cc-runtime/logs/manual-tests-33.md` : scénarios de validation extension (popup, bandeau, fill, suggest, i18n)
- [ ] T037 Vérifier coverage backend ≥ 80 % sur `backend/app/extension/` via `pytest --cov=app.extension`
- [ ] T038 Lint backend (`ruff check backend/app/extension/`) et formatage (`ruff format backend/app/extension/`)

## Dependencies

- T001-T002 (setup) doivent précéder T003-T008
- T003 doit précéder T004 (modèles dépendent du schéma DB)
- T004-T005 doivent précéder T006-T007 (services utilisent modèles + schemas)
- T008 doit précéder phases 3-9 (CORS sinon extension bloquée)
- US1 (T009-T014) bloque US2-US7 côté extension (login préalable requis)
- US2 (T015-T019) bloque US3 (T020 étend content.js posé en T019)
- US4 (T021-T025) dépend de US1 (profile-summary) et US2 (field_mappings join)
- US5 (T026-T028) dépend de T010 (profile-summary disponible) et T027 (LLM client)
- Admin phase 10 indépendante de l'extension JS, peut s'exécuter en parallèle de toute phase backend
- Polish (T035-T038) en dernier

## Parallel Execution Examples

**US1 parallèle** : T009 ‖ T011 ‖ T012 ‖ T014 — ensuite T010 puis T013.
**US2 parallèle** : T015 ‖ T016 ‖ T018 — ensuite T017 puis T019.
**US4 parallèle** : T021 ‖ T024 — ensuite T022, T023, T025.
**Admin** : T032 puis T033 puis T034.

## Implementation Strategy

**MVP minimal vert (livrable)** : Setup + Foundational + US1 (login + profile-summary backend) + US2 (url-patterns + bandeau) + Admin (T032-T034) + Polish.

**Squelette extension** : manifest + popup + content.js minimal couvrant US1+US2 ; US3-US7 finalisés si temps disponible, sinon documentés `DEFERRED` dans manual-tests.

**Couverture cible** : backend ≥ 80 %, extension JS testée manuellement (log dans `.cc-runtime/logs/manual-tests-33.md`).
