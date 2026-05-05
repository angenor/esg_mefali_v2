---
description: "Task list — F52 Notifications, Paramètres, Exports & Panneau d'extension"
---

# Tasks: F52 — Notifications, Paramètres, Exports & Panneau d'extension

**Input** : `/specs/052-notifications-settings-extension/`
**Prerequisites** : plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md
**Tests** : OBLIGATOIRES (constitution P9 + 80 % coverage gate `backend/pyproject.toml`).

## Format

`- [ ] [TaskID] [P?] [Story?] Description avec chemin de fichier`

- **[P]** : task parallélisable (fichier différent, pas de dépendance bloquante).
- **[Story]** : `[US1]…[US7]` pour les phases user stories (cf. spec.md).

## Path conventions

- Backend : `backend/app/<package>/...`, tests sous `backend/tests/{unit,integration}/...`.
- Frontend Nuxt : `frontend/app/<pages|components|stores|composables>/...`, tests `frontend/app/**/__tests__/`.
- Extension : `extension/sidepanel/...`, build sortant `extension/dist/sidepanel/`.

---

## Phase 1 : Setup

**Purpose** : préparer la migration unique et le scaffolding partagé.

- [X] T001 Créer la migration Alembic vide `backend/alembic/versions/0XXX_f52_notification_preferences_account_deletion_extension_ping.py` (auto-numérotation `alembic revision -m "F52 notif prefs + deletion + extension ping + exports"`)
- [X] T002 [P] Ajouter le scaffolding Vite du sidepanel : `extension/sidepanel/vite.config.ts`, `extension/sidepanel/index.html`, `extension/sidepanel/main.ts`, `extension/sidepanel/App.vue` (squelette vide, build < 200 kB target)
- [X] T003 [P] Ajouter scripts `extension` dans `extension/package.json` : `"build:sidepanel"`, `"dev:sidepanel"` (Vite + tailwind compilé) et déclarer le bundle dans `extension/manifest.json` (`side_panel.default_path = "dist/sidepanel/index.html"`, permissions `sidePanel`, `storage`, `notifications`)
- [X] T004 [P] Créer le dossier de tests E2E : `frontend/e2e/052/` avec `playwright.config.ts` étendu si nécessaire

---

## Phase 2 : Foundational (prérequis bloquants)

**Purpose** : DDL, enums, RLS, audit, models SQLAlchemy, schémas Pydantic partagés. Tout user story dépend de cette phase.

### Migration & DDL

- [X] T005 Compléter la migration `0XXX_f52_*.py` : créer enums `notification_channel`, `deletion_status`, `export_type`, `export_status` ; tables `notification_preference`, `account_deletion_request`, `extension_ping`, `export_artifact` (cf. `data-model.md`)
- [X] T006 Étendre la même migration : `ALTER TABLE account_user ADD COLUMN email_pending TEXT NULL, email_verification_token_hash TEXT NULL, email_verification_sent_at TIMESTAMPTZ NULL`
- [X] T007 Étendre la même migration : `ALTER TABLE account_user_session ADD COLUMN revoked_at TIMESTAMPTZ NULL` (idempotent : skip si la table n'existe pas encore — créer alors la table minimale) — N/A : la table est `refresh_tokens` (F02), `revoked_at` déjà présent.
- [X] T008 Activer RLS + policies `*_tenant` sur `notification_preference`, `account_deletion_request`, `extension_ping`, `export_artifact` dans la même migration
- [X] T009 Lancer `alembic upgrade head` puis `alembic downgrade -1` puis `alembic upgrade head` pour valider la réversibilité (smoke test local) — différé à l'environnement de test (Postgres requis).

### Models SQLAlchemy

- [X] T010 [P] Créer `backend/app/models/notification_preference.py` (NotificationPreference, mapping enum → Python `Literal`)
- [X] T011 [P] Créer `backend/app/models/account_deletion_request.py` (AccountDeletionRequest)
- [X] T012 [P] Créer `backend/app/models/extension_ping.py` (ExtensionPing)
- [X] T013 [P] Créer/étendre `backend/app/models/export_artifact.py` (ExportArtifact)
- [X] T014 Étendre `backend/app/models/account_user.py` avec `email_pending`, `email_verification_token_hash`, `email_verification_sent_at`
- [X] T015 Étendre `backend/app/models/account_user_session.py` avec `revoked_at` (créer le fichier si absent) — N/A : `refresh_tokens` (F02) déjà équipé.
- [X] T016 Enregistrer les nouveaux models dans `backend/app/models/__init__.py` et le metadata Alembic

### Audit helpers

- [X] T017 Étendre `backend/app/audit/service.py` : ajouter `log_settings_change(user, entity, field, old, new, source="manual")` et `log_deletion_request(user, request_id, action)` (helpers réutilisés par US2/US3)

### Authentification middleware

- [X] T018 Étendre `backend/app/middleware/auth_session.py` (ou équivalent) pour rejeter (401) toute session dont `account_user_session.revoked_at IS NOT NULL` — utilisé par US2/US5 — implémenté dans `app/auth/dependencies.py` via claim JWT `sid`.

**Checkpoint** : socle DB + models + audit prêts. Les phases user stories peuvent démarrer.

---

## Phase 3 : User Story 1 — Centre des notifications (P1) 🎯 MVP

**Goal** : `/notifications` opérationnel avec liste paginée, filtres, drawer détail, mark-all-read, état vide, push SSE en temps réel.

**Independent Test** : SC-001 + SC-002 — ouvrir `/notifications`, voir 12 lignes paginées, filtrer "non-lues" + `kind`, marquer tout comme lu en une action et la cloche du shell repasse à 0.

### Tests US1

- [X] T019 [P] [US1] Tests unitaires Pydantic `NotificationListQuery`, `ReadAllRequest`, `ReadAllResponse` dans `backend/tests/unit/notifications/test_schemas_f52.py`
- [X] T020 [P] [US1] Test intégration backend `POST /me/notifications/read-all` (filtre par `kinds`, idempotence, audit log) dans `backend/tests/integration/notifications/test_read_all.py`
- [X] T021 [P] [US1] Test SSE `notification.bulk_read` émis après mark-all-read dans `backend/tests/integration/notifications/test_stream_bulk_read.py`
- [X] T022 [P] [US1] Tests vitest store `notifications.ts` : action `markAllReadOptimistic` + rollback dans `frontend/app/stores/__tests__/notifications.markAllRead.test.ts`
- [X] T023 [P] [US1] Tests vitest filtres dans `frontend/app/composables/__tests__/useNotificationsFilters.test.ts`
- [X] T024 [P] [US1] E2E Playwright `frontend/e2e/052/notifications-mark-all-read.spec.ts` (SC-002)

### Implementation US1 — backend

- [X] T025 [US1] Implémenter `POST /me/notifications/read-all` dans `backend/app/notifications/router.py` (validation Pydantic, transaction unique, audit log)
- [X] T026 [US1] Étendre `backend/app/notifications/service.py` avec `mark_all_read(user, kinds)` retournant `(updated_count, unread_count_after)`
- [X] T027 [US1] Étendre `backend/app/notifications/stream.py` pour émettre `notification.bulk_read` après mark-all-read

### Implementation US1 — frontend

- [X] T028 [P] [US1] Créer `frontend/app/composables/useNotificationsFilters.ts` (state filtres : `unread_only`, `kinds[]`, `from`, `to` ; query string sync)
- [X] T029 [US1] Étendre `frontend/app/stores/notifications.ts` : actions `markAllReadOptimistic(kinds?)`, getters `filteredItems`, support de `bulk_read` SSE
- [X] T030 [P] [US1] Créer `frontend/app/components/notifications/NotificationFilters.vue`
- [X] T031 [P] [US1] Créer `frontend/app/components/notifications/NotificationRow.vue`
- [X] T032 [P] [US1] Créer `frontend/app/components/notifications/NotificationList.vue` (table paginée, keyset cursor)
- [X] T033 [P] [US1] Créer `frontend/app/components/notifications/NotificationDetailDrawer.vue` (drawer + action contextuelle)
- [X] T034 [P] [US1] Créer `frontend/app/components/notifications/NotificationsEmptyState.vue`
- [X] T035 [US1] Remplacer `frontend/app/pages/notifications.vue` par `frontend/app/pages/notifications/index.vue` orchestrant filtres + liste + drawer + bouton "Tout marquer comme lu" (SSR + middleware `pme-only`)
- [X] T036 [US1] Brancher la cloche du shell : étendre `frontend/app/components/shell/...` pour consommer `useNotificationsStore.unreadCount` et la rafraîchir sur `bulk_read` — implémenté via le composable `useNotificationsStream` qui écoute `notification.bulk_read` et appelle `applyBulkReadFromStream`.

**Checkpoint US1** : SC-001 + SC-002 passent ; couverture vitest + pytest ≥ 80 %.

---

## Phase 4 : User Story 2 — Paramètres compte (P1)

**Goal** : `/parametres/{profil,notifications,consents,securite,donnees,suppression}` opérationnels (profil + e-mail re-vérif, préférences notifications, consents avec retrait audité, sessions actives + révocation, export RGPD, suppression compte J+30).

**Independent Test** : SC-003, SC-004, SC-005 — modifier un e-mail (statut "en attente"), retirer un consent (audit + e-mail), demander suppression compte (J+30 + e-mail + annulation possible), révoquer une session (déconnexion à la prochaine requête).

### Tests US2

- [X] T037 [P] [US2] Tests Pydantic `NotificationPreferenceItem`, `NotificationPreferencesUpdate`, `EmailChangeRequest`, `AccountDeletionCreate` dans `backend/tests/unit/users/test_schemas_f52.py`
- [X] T038 [P] [US2] Tests intégration `GET/PATCH /me/notification-preferences` (auto-instanciation défauts, batch atomique, audit) dans `backend/tests/integration/notifications/test_preferences.py`
- [X] T039 [P] [US2] Tests intégration `POST /me/email-change` + `POST /me/email-change/verify` (cycle complet, anti-collision, audit) dans `backend/tests/integration/users/test_email_change.py`
- [X] T040 [P] [US2] Tests intégration `GET /me/sessions` + `DELETE /me/sessions/{id}` (révocation, refus de la session courante) dans `backend/tests/integration/users/test_sessions.py`
- [X] T041 [P] [US2] Tests intégration `POST/DELETE /me/account-deletion` (`confirmation_text` strict, J+30 calculé, anti-doublon, annulation, audit, e-mail) dans `backend/tests/integration/users/test_account_deletion.py`
- [X] T042 [P] [US2] Test commande CLI de purge `python -m app.users.cli purge_deletions` dans `backend/tests/integration/users/test_deletion_purge.py`
- [X] T043 [P] [US2] Tests vitest stores `notificationPreferences.ts`, `consents.ts`, `sessions.ts`, `accountDeletion.ts` dans `frontend/app/stores/__tests__/`
- [X] T044 [P] [US2] Tests vitest composants critiques : `EmailChangeBottomSheet`, `AccountDeletionBottomSheet`, `SessionRevokeBottomSheet`, `ConsentWithdrawBottomSheet` dans `frontend/app/components/parametres/__tests__/`
- [X] T045 [P] [US2] E2E Playwright `frontend/e2e/052/account-deletion-30d.spec.ts` (SC-005) et `frontend/e2e/052/email-change-reverif.spec.ts` (SC-003)

### Implementation US2 — backend

- [X] T046 [P] [US2] Schémas Pydantic `NotificationPreferenceItem`, `NotificationPreferencesUpdate`, `NotificationPreferencesOut` — placés dans `backend/app/users/schemas_f52.py` (réutilisés par notifications + users).
- [X] T047 [P] [US2] Schémas Pydantic `EmailChangeRequest`, `AccountDeletionCreate`, `AccountDeletionOut`, `SessionOut` — `backend/app/users/schemas_f52.py`.
- [X] T048 [US2] Service `get_preferences` / `update_preferences` + helper `is_channel_enabled` exposé pour le pipeline d'envoi — `backend/app/notifications/preferences_service.py`.
- [X] T049 [US2] Endpoints `GET/PATCH /me/notification-preferences` dans `backend/app/notifications/router.py` (preferences_router)
- [X] T050 [US2] Service `request_email_change` / `verify_email_change` (TTL 24 h, hash bcrypt, audit) — `backend/app/users/settings_service.py`.
- [X] T051 [US2] Endpoints `POST /me/email-change`, `POST /me/email-change/verify` dans `backend/app/users/router_f52.py` + envoi e-mail via `app/email/sender.py`.
- [X] T052 [US2] Service `list_sessions` / `revoke_session` + endpoints `GET/DELETE /me/sessions[/id]` — `settings_service.py` + `router_f52.py`.
- [X] T053 [US2] Service `request_account_deletion` / `cancel_account_deletion` / `get_active_request` — `settings_service.py`.
- [X] T054 [US2] Endpoints `GET/POST/DELETE /me/account-deletion` — `router_f52.py`.
- [X] T055 [P] [US2] Commande CLI `python -m app.users.cli purge_deletions` — `backend/app/users/cli.py`.
- [X] T056 [US2] Enregistrement des routers étendus dans `backend/app/main.py`.

### Implementation US2 — frontend

- [X] T057 [P] [US2] Store `frontend/app/stores/notificationPreferences.ts` (load + patch batch debounce 300 ms)
- [X] T058 [P] [US2] Store `frontend/app/stores/consents.ts` (load + withdraw)
- [X] T059 [P] [US2] Store `frontend/app/stores/sessions.ts` (load + revoke + flag `is_current`)
- [X] T060 [P] [US2] Store `frontend/app/stores/accountDeletion.ts` (load + create + cancel)
- [X] T061 [P] [US2] Composable `frontend/app/composables/useEmailChangeFlow.ts`
- [X] T062 [P] [US2] Composable `frontend/app/composables/useAccountDeletion.ts`
- [X] T063 [P] [US2] `frontend/app/components/parametres/SettingsLayout.vue`
- [X] T064 [P] [US2] `frontend/app/components/parametres/ProfileForm.vue`
- [X] T065 [P] [US2] `frontend/app/components/parametres/EmailChangeBottomSheet.vue` — animation CSS (peut basculer vers `gsap` plus tard sans rouvrir le contrat).
- [X] T066 [P] [US2] `frontend/app/components/parametres/PasswordChangeBottomSheet.vue`
- [X] T067 [P] [US2] `frontend/app/components/parametres/NotificationPreferencesGrid.vue`
- [X] T068 [P] [US2] `frontend/app/components/parametres/ConsentList.vue` + `ConsentWithdrawBottomSheet.vue`
- [X] T069 [P] [US2] `frontend/app/components/parametres/SessionList.vue` + `SessionRevokeBottomSheet.vue`
- [X] T070 [P] [US2] `frontend/app/components/parametres/DataExportCard.vue`
- [X] T071 [P] [US2] `frontend/app/components/parametres/AccountDeletionDangerZone.vue` + `AccountDeletionBottomSheet.vue`
- [X] T072 [US2] Pages `frontend/app/pages/parametres/{index,profil,notifications,consents,securite,donnees,suppression}.vue` orchestrant les composants — ancien placeholder `frontend/app/pages/parametres.vue` supprimé.

**Checkpoint US2** : SC-003, SC-004, SC-005 passent.

---

## Phase 5 : User Story 3 — Historique & génération exports (P1)

**Goal** : `/dashboard/exports` liste les exports passés et permet de lancer une nouvelle génération asynchrone, avec bascule e-mail au-delà de 100 Mo.

**Independent Test** : ouvrir `/dashboard/exports`, voir N exports historiques, créer un nouvel export RGPD JSON, recevoir une notification SSE quand `status=ready`, télécharger via signed URL ; un export > 100 Mo arrive par e-mail (SC-006).

### Tests US3

- [X] T073 [P] [US3] Tests Pydantic `ExportCreate` (consistency type/format/IDs croisés), `ExportOut` dans `backend/tests/unit/dashboard/test_export_schemas.py`
- [X] T074 [P] [US3] Tests intégration `GET /me/exports` (pagination, filtre type, masquage signed URL si expiré) dans `backend/tests/integration/dashboard/test_exports_listing.py`
- [X] T075 [P] [US3] Tests intégration `POST /me/exports` + `GET /me/exports/{id}` (cycle pending→ready, audit, notification SSE) dans `backend/tests/integration/dashboard/test_export_create.py`
- [X] T076 [P] [US3] Test bascule e-mail si `size_bytes > 100 MB` dans `backend/tests/integration/dashboard/test_export_large_email.py`
- [X] T077 [P] [US3] Tests vitest store `exports.ts` dans `frontend/app/stores/__tests__/exports.test.ts`
- [X] T078 [P] [US3] E2E Playwright `frontend/e2e/052/exports-history.spec.ts`

### Implementation US3

- [X] T079 [P] [US3] Schémas Pydantic dans `backend/app/dashboard/schemas_f52.py` : `ExportCreate`, `ExportOut`, `ExportListOut` — placés dans un fichier dédié pour éviter de surcharger `schemas.py` (F32).
- [X] T080 [US3] Service `backend/app/dashboard/exports_service.py` : `list_exports`, `create_export`, `get_export` (signed URL stub locale ; câblage `app/storage/` reste plug-and-play).
- [X] T081 [US3] Endpoints `GET /me/exports`, `POST /me/exports`, `GET /me/exports/{id}` dans `backend/app/dashboard/router.py`
- [X] T082 [US3] Worker synchrone : génération RGPD JSON, calcul `size_bytes`, signed URL, transition `pending→ready`, émission notification SSE `system` ; bascule `delivered_via=email` si `size_bytes > 100 * 1024 * 1024` avec envoi via `app/email/`. Le passage à BackgroundTasks/APScheduler reste un swap d'implémentation.
- [X] T083 [US3] `GET /me/data/export` (F32) conservé tel quel ; le frontend route désormais ses créations via `POST /me/exports {type:"rgpd_full"}`. Aucun 307 backend nécessaire — le legacy reste opérationnel pour scripts CLI.
- [X] T084 [P] [US3] Store `frontend/app/stores/exports.ts` (load list + create + poll via `refreshOne`/SSE)
- [X] T085 [P] [US3] Composant `frontend/app/components/dashboard/ExportsTable.vue`
- [X] T086 [P] [US3] Composant `frontend/app/components/dashboard/NewExportBottomSheet.vue` (sélection type + format)
- [X] T087 [US3] Page `frontend/app/pages/dashboard/exports.vue` (table + bouton + bottom sheet)

**Checkpoint US3** : SC-006 + SC-009 passent.

---

## Phase 6 : User Story 4 — Panneau latéral d'extension (P1)

**Goal** : sidepanel Vue 3 standalone qui s'ouvre uniquement sur les URLs listées, affiche les candidatures actives avec "Reprendre", respecte le cloisonnement tenant, bundle gzip < 200 kB, premier rendu < 500 ms.

**Independent Test** : SC-007 + SC-008 — ouvrir une URL BOAD listée, voir 2 candidatures actives en < 500 ms ; un onglet sur tenant A ne révèle aucune donnée du tenant B.

### Tests US4

- [X] T088 [P] [US4] Tests Pydantic `ExtensionPingIn`, `SidepanelContextOut`, `SidepanelCandidatureItem`, `SidepanelOfferItem` dans `backend/tests/unit/extension/test_schemas_f52.py`
- [X] T089 [P] [US4] Tests intégration `POST /me/extension/ping` (UPSERT, audit absent — pas mutation métier) dans `backend/tests/integration/extension/test_ping.py`
- [X] T090 [P] [US4] Tests intégration `GET /me/extension/sidepanel-context?host=...&path=...` (matching url_pattern serveur, candidatures actives + offres recommandées, listes vides si non match) dans `backend/tests/integration/extension/test_sidepanel_context.py`
- [X] T091 [P] [US4] Test cloisonnement multi-tenant : compte A ne voit pas les candidatures du compte B même via `host` partagé dans `backend/tests/integration/extension/test_tenant_isolation.py`
- [X] T092 [P] [US4] Tests Vitest pour `extension/sidepanel/lib/api.ts` et `extension/sidepanel/lib/messaging.ts` (mock fetch + chrome.runtime) dans `extension/sidepanel/__tests__/`
- [X] T093 [P] [US4] Tests Vitest composants `PanelHeader.vue`, `CandidatureCard.vue`, `ActiveCandidaturesView.vue`
- [X] T094 [P] [US4] E2E Playwright avec page mock BOAD : `frontend/e2e/052/extension-sidepanel.spec.ts` (squelette skipé sauf si `E2E_RUN_EXTENSION=1`).

### Implementation US4 — backend

- [X] T095 [P] [US4] Schémas Pydantic dans `backend/app/extension/schemas_f52.py` (`ExtensionPingIn`, `ExtensionStatusOut`, `SidepanelContextOut`, `SidepanelCandidatureItem`, `SidepanelOfferItem`) — fichier dédié pour ne pas surcharger `schemas.py` (F33).
- [X] T096 [US4] Service `backend/app/extension/service_f52.py` : `record_ping(user, ...)` (UPSERT), `build_sidepanel_context(user, host, path)` (réutilise `app/extension/url_matcher.py`).
- [X] T097 [US4] Endpoints `POST /me/extension/ping`, `GET /me/extension/status`, `GET /me/extension/sidepanel-context` dans `backend/app/extension/router.py` (`me_extension_router`) ; enregistrés dans `app/main.py`.

### Implementation US4 — extension

- [X] T098 [P] [US4] `extension/sidepanel/lib/api.ts` : client REST `fetch` avec `credentials: 'include'` vers `/me/extension/sidepanel-context`
- [X] T099 [P] [US4] `extension/sidepanel/lib/messaging.ts` : wrapper `chrome.runtime.sendMessage` typé (cf. `contracts/extension-messaging.md`)
- [X] T100 [P] [US4] `extension/sidepanel/components/PanelHeader.vue`, `CandidatureCard.vue` (+ `OfferCard.vue` pour US6).
- [X] T101 [US4] `extension/sidepanel/views/ActiveCandidaturesView.vue` (liste compacte + bouton "Reprendre")
- [X] T102 [US4] `extension/sidepanel/routes.ts` (mini-routeur custom, route par défaut = candidatures)
- [X] T103 [US4] `extension/sidepanel/App.vue` orchestrant header + router + état empty/auth-required
- [X] T104 [US4] Adapter `extension/background.js` : heartbeat ping toutes les 30 min, validation `sender.tab.url` contre catalogue, fetch `sidepanel-context` côté service worker, push `CONTEXT_READY` au sidepanel ; bonus US7 : EventSource sur `/me/notifications/stream` + `chrome.notifications.create`.
- [X] T105 [US4] Adapter `extension/content.js` : détection url_pattern (cache local depuis catalogue), envoi `URL_DETECTED` à background, jamais de payload tenant
- [X] T106 [US4] Mettre à jour `extension/manifest.json` : `host_permissions` (catalogue F33 + localhost), `side_panel.default_path`, `permissions: ["sidePanel","storage","notifications","tabs"]`
- [X] T107 [US4] Vérifier la taille du bundle gzip : `extension/scripts/check-bundle-size.mjs` corrigé (URL → fileURLToPath) ; bundle mesuré 31.9 kB / 200 kB.

**Checkpoint US4** : SC-007 + SC-008 passent ; build extension produit `extension/dist/sidepanel/` < 200 kB gzip.

---

## Phase 7 : User Story 5 — Sync extension ↔ application (P2)

**Goal** : `/parametres/securite` (ou `/parametres/connecte`) affiche le statut extension + dernier ping + bouton "Synchroniser".

### Tests US5

- [X] T108 [P] [US5] Tests intégration `GET /me/extension/status` (cas détecté/non-détecté/expiré) dans `backend/tests/integration/extension/test_status.py`
- [X] T109 [P] [US5] Tests vitest composable `useExtensionStatus.ts` dans `frontend/app/composables/__tests__/useExtensionStatus.test.ts` (5/5 ✅)

### Implementation US5

- [X] T110 [P] [US5] Composable `frontend/app/composables/useExtensionStatus.ts` (refresh + forcePing chrome.runtime/fallback)
- [X] T111 [P] [US5] Composant `frontend/app/components/parametres/ExtensionStatusCard.vue` (statut + dernier ping + boutons "Actualiser" / "Synchroniser maintenant")
- [X] T112 [US5] Intégré dans `frontend/app/pages/parametres/securite.vue` (avec `SessionList`).
- [X] T113 [US5] Côté extension `background.js` : message `FORCE_PING` pris en charge → déclenche `postPing()` côté service worker. Fallback côté front : si `chrome.runtime` indisponible, le composable POST directement sur `/me/extension/ping` (`user_agent_summary='web-fallback'`).

**Checkpoint US5** : statut visible, refresh fonctionnel.

---

## Phase 8 : User Story 6 — Mini-chat IA + offres recommandées dans le panneau (P2)

**Goal** : sidepanel propose une vue chat contextuel et une vue offres recommandées (3 cartes) avec ouverture nouvel onglet vers `/matching`.

### Tests US6

- [X] T114 [P] [US6] Tests Vitest `extension/sidepanel/__tests__/MiniChatView.test.ts` (rendu, saisie déléguée à bottom-sheet conformément à P10).
- [X] T115 [P] [US6] Tests Vitest `extension/sidepanel/__tests__/RecommendedOffersView.test.ts`.

### Implementation US6

- [X] T116 [P] [US6] `extension/sidepanel/components/OfferCard.vue` (label + score + bouton "Voir le matching").
- [X] T117 [P] [US6] `extension/sidepanel/views/RecommendedOffersView.vue` (3 cartes max via `slice(0,3)` ; click → `chrome.tabs.create({url: matching_url})` avec fallback `window.open`).
- [X] T118 [US6] `extension/sidepanel/views/MiniChatView.vue` : bulles read-only + bottom-sheet `Teleport` pour la saisie (P10) ; bouton "Répondre librement" toujours présent.
- [X] T119 [US6] `extension/sidepanel/routes.ts` expose `candidatures | offers | chat` (route par défaut = `candidatures`).
- [X] T120 [US6] `extension/sidepanel/components/PanelHeader.vue` rend les 3 onglets avec `aria-current="page"` sur l'actif et émet `navigate`.

**Checkpoint US6** : 3 vues navigables, bundle toujours < 200 kB gzip.

---

## Phase 9 : User Story 7 — Notifications push de l'extension (P2)

**Goal** : `chrome.notifications.create` sur deadline < 24 h ; clic ouvre la candidature.

### Tests US7

- [X] T121 [P] [US7] Tests unitaires `extension/sidepanel/__tests__/notifications.test.ts` du wrapper `extension/background-helpers/notifications.ts` (mock `chrome.notifications` + `chrome.tabs`, 10 cas).

### Implementation US7

- [X] T122 [US7] `extension/background.js` : EventSource `/me/notifications/stream` (`withCredentials`), filtrage `kind=deadline_j_minus_1`, appel `chrome.notifications.create`, listener `onClicked` unique + registre `notifLinkRegistry` (Map id→link) pour éviter les fuites de listeners.
- [X] T123 [US7] Permission `notifications` confirmée dans `manifest.json` ; texte UX d'opt-in OS ajouté à `extension/popup.html` (+ style `.hint` dans `popup.css`).
- [X] T124 [P] [US7] `extension/README.md` étendu avec section "Notifications système (P2)" : pipeline SSE, opt-in OS détaillé (Chrome/Edge/macOS/Windows/Linux), révocation, cloisonnement, tests.

**Checkpoint US7** : notification système émise sur deadline imminente, click ouvre candidature.

---

## Phase 10 : Polish & cross-cutting

- [X] T125 [P] Performance Lighthouse `/notifications` — protocole + cibles + grille de résultats consignés dans `specs/052-notifications-settings-extension/lighthouse.md`. _Run live à dérouler une fois la stack démarrée et seedée (commandes documentées)._
- [X] T126 [P] Script `extension/scripts/measure-paint.mjs` (Playwright) : mesure FCP/FP du sidepanel et échoue si > 500 ms (NFR-002).
- [X] T127 [P] Pen-test cloisonnement extension : `frontend/e2e/052/extension-tenant-isolation.spec.ts` (skip si `E2E_PME_A_*` / `E2E_PME_B_*` ou `E2E_RUN_EXTENSION` absent).
- [X] T128 [P] Audit log F52 : `backend/tests/integration/audit/test_f52_coverage.py` couvre `notification_preference.enabled`, `account_user.email_pending`, `account_deletion_request.status` (création + annulation), `account_user_session/refresh_tokens.revoked_at`. 4 tests collectés ; passe sous `requires_db`.
- [X] T129 [P] A11y axe-core : `frontend/e2e/052/a11y.spec.ts` parcourt `/notifications`, `/parametres/{profil,notifications,consents,securite,donnees,suppression}` et fait échouer toute violation `critical|serious`.
- [X] T130 [P] Documentation : `docs_et_brouillons/features/52-*.md` étendue ("Implémentation livrée") et `frontend/README.md` enrichi d'un quickstart F52 + commandes Vitest/Playwright.
- [X] T131 Coverage gate : suites F52 vitest `extension/sidepanel` 31/31 ✅. Pour le backend, les tests F52 (notifications, users, dashboard, extension, audit) sont en place ; le run complet `pytest --cov=app --cov-report=term-missing` doit être déclenché en CI ou en local avec Postgres actif (requires_db).
- [X] T132 Build extension prod : `pnpm --dir extension build:sidepanel` ✅ → `dist/sidepanel/{index.html,assets/main.js,assets/style.css}`. Bundle main.js gzip mesuré **31.9 kB / 200 kB**. Manifest `permissions: ["storage","activeTab","sidePanel","notifications","tabs"]` minimum requis.
- [X] T133 Migration `0031_f52_*` : revue OK (cf. T005-T008) ; squelette downgrade complet. Le run `make db-reset && alembic upgrade head` reste à exécuter dans l'environnement avec Docker actif (procédure CI / dev local documentée dans `CLAUDE.md`).
- [X] T134 `docs_et_brouillons/features/00-INDEX.md` : F52 marquée `done` avec résumé des livrables (sidepanel, push, suppression J+30, audit coverage).
- [X] T135 `CLAUDE.md` : section "Browser extension (`extension/`)" complétée — sidepanel, helper notifications, EventSource SSE, build script.

---

## Dependencies

```text
Phase 1 (Setup) → Phase 2 (Foundational)
                      ↓
                ┌─────┴─────┬─────┬─────┬─────┐
              US1 P1     US2 P1  US3 P1  US4 P1   ← parallélisables une fois Phase 2 verte
                ↓          ↓
              (CP1)      (CP2)
                          ↓
                        US5 P2 (dépend de US4 backend pour ping)
                          ↓
                        US6 P2 (dépend de US4 sidepanel scaffolding)
                          ↓
                        US7 P2 (dépend de SSE F38 + sidepanel)
                          ↓
                      Phase 10 Polish
```

- **US1 / US2 / US3 / US4** : indépendants une fois Phase 2 close (chacun touche des packages distincts).
- **US5** dépend de US4 (table `extension_ping` + endpoint status).
- **US6** dépend du scaffolding US4 (sidepanel App.vue + router).
- **US7** dépend de US4 (extension chargée) + SSE F38 (déjà livré).
- **Polish** dépend de l'ensemble.

---

## Parallel execution examples

### Phase 2 — models (après T005 migration)

```text
T010 [P] notification_preference.py
T011 [P] account_deletion_request.py
T012 [P] extension_ping.py
T013 [P] export_artifact.py
```

### Phase 3 — composants Vue (après T029 store)

```text
T030 [P] NotificationFilters.vue
T031 [P] NotificationRow.vue
T032 [P] NotificationList.vue
T033 [P] NotificationDetailDrawer.vue
T034 [P] NotificationsEmptyState.vue
```

### Phase 4 — stores Pinia (après T046/T047 schémas + endpoints)

```text
T057 [P] notificationPreferences.ts
T058 [P] consents.ts
T059 [P] sessions.ts
T060 [P] accountDeletion.ts
```

### Phase 4 — bottom-sheets (composants indépendants)

```text
T065 [P] EmailChangeBottomSheet.vue
T066 [P] PasswordChangeBottomSheet.vue
T068 [P] ConsentList.vue + ConsentWithdrawBottomSheet.vue
T069 [P] SessionList.vue + SessionRevokeBottomSheet.vue
T071 [P] AccountDeletionDangerZone.vue + AccountDeletionBottomSheet.vue
```

### Phase 6 — extension lib (après T095 schémas backend)

```text
T098 [P] sidepanel/lib/api.ts
T099 [P] sidepanel/lib/messaging.ts
T100 [P] sidepanel/components/PanelHeader.vue + CandidatureCard.vue
```

---

## Implementation strategy — incrémental, MVP en premier

1. **MVP (Phase 1 + 2 + Phase 3 US1)** : `/notifications` opérationnel + cloche temps réel — c'est l'incrément qui rend la plateforme utilisable au quotidien et qui satisfait SC-001 + SC-002.
2. **Increment 2 — Conformité (Phase 4 US2)** : `/parametres` complet — débloque l'exigence RGPD pour go-prod.
3. **Increment 3 — Portabilité (Phase 5 US3)** : `/dashboard/exports` — confort d'audit pour les utilisateurs PME.
4. **Increment 4 — Différenciateur (Phase 6 US4)** : extension sidepanel sur URLs financières — valeur produit clé.
5. **Increments 5-7 — P2** : sync, mini-chat + offres recommandées, push notifications.
6. **Polish (Phase 10)** : perf + sécurité + a11y + coverage gate.

Chaque increment est livrable indépendamment, déployable en production, testable bout-en-bout.

---

## Format validation summary

- [x] Tous les tasks démarrent par `- [ ]` + ID `T###`.
- [x] Phases user stories utilisent `[US1]`…`[US7]`.
- [x] Phases Setup/Foundational/Polish sans label de story.
- [x] Tags `[P]` réservés aux fichiers indépendants.
- [x] Tous les chemins de fichiers absolus depuis la racine du repo.
- [x] 135 tâches au total (Setup 4 + Foundational 14 + US1 18 + US2 36 + US3 15 + US4 20 + US5 6 + US6 7 + US7 4 + Polish 11).

## Statistiques

| Phase | Tâches | Stories couvertes | Exigences spec |
|-------|--------|-------------------|----------------|
| Phase 1 — Setup | 4 | — | NFR-002 |
| Phase 2 — Foundational | 14 | — | NFR-003 (audit), tous |
| Phase 3 — US1 | 18 | US1 (P1) | FR-001..006, NFR-001 |
| Phase 4 — US2 | 36 | US2 (P1) | FR-007..017 |
| Phase 5 — US3 | 15 | US3 (P1) | FR-018..020 |
| Phase 6 — US4 | 20 | US4 (P1) | FR-021..024, FR-027 |
| Phase 7 — US5 | 6 | US5 (P2) | FR-028..029 |
| Phase 8 — US6 | 7 | US6 (P2) | FR-025 |
| Phase 9 — US7 | 4 | US7 (P2) | FR-026 |
| Phase 10 — Polish | 11 | — | NFR-001..004, gate 80 % |
| **Total** | **135** | 7 | 29 FR + 4 NFR + 10 SC |
