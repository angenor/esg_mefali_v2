# Implementation Plan: Notifications, Paramètres, Exports & Panneau d'extension

**Branch**: `052-notifications-settings-extension` | **Date**: 2026-05-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/052-notifications-settings-extension/spec.md`

## Summary

F52 livre les **surfaces UI de réglages secondaires** : `/notifications` (centre paginé + filtres + détail + temps réel), `/parametres` (profil, préférences canaux, RGPD/consents, sessions, export, suppression J+30), `/dashboard/exports` (historique + nouvelle génération), et un **panneau latéral d'extension** Chromium qui s'injecte sur les URLs de plateformes financières listées (catalogue F33) pour afficher les candidatures actives, un mini-chat IA contextuel et 3 cartes d'offres compatibles. Pas de nouveaux endpoints métier majeurs : la feature **consomme** ce qui existe déjà côté backend (`app/notifications/`, `/me/notifications`, `/me/notifications/{id}/read`, SSE F38, `/me/data/export` F32, `/me/preferences` F42, `/me/consents` privacy, sessions auth) et complète le manquant (préférences notifications par kind, suppression de compte planifiée J+30, export listing dédié, ping extension) avec une chirurgie minimale dans `app/users/` et `app/extension/`. Côté front, on s'appuie sur le store Pinia `notifications` et le composable `useNotificationsStream` déjà en place ; côté extension on étend l'extension MV3 existante (`extension/`) en ajoutant un build Vue 3 standalone du sidepanel.

## Technical Context

**Language/Version** : Python 3.12+ (backend FastAPI), TypeScript 5.x / Node 20.x (frontend Nuxt 4 + extension Vite).
**Primary Dependencies** : FastAPI + SQLAlchemy + Alembic (backend) ; Nuxt 4 + Vue 3 + Pinia + Tailwind v4 + gsap + nuxt-security (frontend) ; Vue 3 + Vite standalone build pour `extension/sidepanel/`.
**Storage** : PostgreSQL + RLS (tables existantes `notification`, ajout `notification_preference`, `account_deletion_request`, `extension_ping`).
**Testing** : pytest + httpx + factory_boy côté backend (markers `unit`/`integration`) ; vitest + @vue/test-utils côté frontend ; Playwright pour scénarios end-to-end clés (mark all read, suppression de compte, panneau extension sur URL listée).
**Target Platform** : Web Nuxt (Chrome/Edge/Brave/Safari/Firefox récents) + extension MV3 Chromium (Chrome/Edge/Brave) — Firefox post-MVP.
**Project Type** : Web application (backend FastAPI + frontend Nuxt) **+ extension navigateur** standalone bundlée séparément.
**Performance Goals** : `/notifications` LCP < 1 s ; mark-all-read optimiste avec rollback ; sidepanel < 200 kB JS gzip et premier rendu < 500 ms post-injection ; flux SSE déjà en place côté backend.
**Constraints** : RGPD (rétention export 30 j ; suppression compte J+30 annulable ; audit log obligatoire sur consents/delete) ; cloisonnement strict tenant ↔ extension (pas de leak `chrome.runtime.sendMessage` cross-account) ; UX bottom sheet pour toute saisie dans le mini-chat extension (P10) ; export RGPD > 100 Mo livré par e-mail.
**Scale/Scope** : ~10 k utilisateurs PME au MVP, ~50 notifications/utilisateur/mois ; ~5 nouvelles pages/composants Nuxt + 1 bundle extension ~150 kB ; backend : ~3 nouveaux endpoints (préférences notifications, deletion-request, exports listing) + 2 augmentations (extension ping, expirations signed url).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principe | Évaluation pour F52 | Statut |
|---|----------|----------------------|--------|
| P1 | Sourçage anti-hallucination | Aucune donnée factuelle ESG/financière introduite par cette UI : elle affiche des notifications, préférences, sessions, exports déjà produits ailleurs. Le mini-chat extension reste une projection des skills existants — pas de nouveau tool factuel sans `cite_source`. | ✅ |
| P2 | Multi-tenant RLS | Toutes nouvelles tables (`notification_preference`, `account_deletion_request`, `extension_ping`) portent `account_id NOT NULL` + politique RLS standard. Les communications extension ↔ API restent JWT cookie + `app.current_account_id` ; aucun message extension ne porte de payload tenant cross-compte. | ✅ |
| P3 | Audit log append-only | Mutations sensibles (modification e-mail, retrait consent, demande suppression compte, révocation session, regen mot de passe) émettent un audit avec `source_of_change=manual`. La purge J+30 émet un audit `source_of_change=admin`/`system`. | ✅ |
| P4 | Versioning + snapshot candidatures | Aucun référentiel/critère touché. Les candidatures référencées dans le panneau extension sont seulement listées (pas de mutation). | ✅ |
| P5 | Money typé | Pas de valeur monétaire manipulée. Les cards d'offres recommandées dans l'extension réutilisent le même `MoneyDisplay` que F25/F51 (pas de duplication). | ✅ |
| P6 | Pivot Indicateur unique | Hors périmètre — pas de stockage ESG nouveau. | ✅ |
| P7 | Plateforme fermée aux intermédiaires | Pas de rôle/canal vers banques/fonds. L'extension surface l'utilisateur PME sur le site du financeur — c'est une lecture côté PME, jamais un push. Les exports restent attestation Ed25519 + page `/verify/{id}` (déjà fournis par F30/F49). | ✅ |
| P8 | Édition manuelle + sync LLM | Tous les champs profil/préférences sont éditables manuellement ; aucune valeur LLM. Le mini-chat extension respecte la sync : si la saisie déclenche une mutation, elle passe par bottom-sheet et invalide le contexte LLM. | ✅ |
| P9 | Tool-use LLM fiable | Le mini-chat extension réutilise `app/orchestrator/` existant ; pas de nouveaux tools introduits par F52. Les éventuelles invocations restent ≤ 2 skills/tour avec validation Pydantic stricte. | ✅ |
| P10 | UX bottom sheet | Toutes les modales paramètres (changement e-mail, retrait consent, suppression compte, révocation session, génération export) passent par bottom-sheet animé gsap. Mini-chat extension : bulles read-only, saisies dans bottom-sheet ; bouton "Répondre librement" toujours présent. | ✅ |

**Verdict** : ✅ pass — aucune violation, pas d'entrée requise dans `Complexity Tracking`.

### Contraintes techniques (rappel — respectées)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL ; LLM via OpenRouter (déjà configuré) ; embeddings Voyage `voyage-3.5` (non utilisés ici).
- Dev local : backend `.venv`, Postgres dockerisé, frontend `pnpm dev`, **extension** ajoutée comme bundle Vite séparé sous `extension/sidepanel/` avec sortie statique chargée par `manifest.json`.
- Hébergement : Europe ou Afrique de l'Ouest uniquement (les liens signed url d'export pointent vers le bucket EU déjà configuré côté `app/storage/`).
- Conformité : RGPD + UEMOA 20/2010 + loi 2013-450 — la suppression J+30, le retrait consent traçable et le seuil export 100 Mo couvrent les exigences.
- Langue : français par défaut sur toutes les surfaces.

## Project Structure

### Documentation (this feature)

```text
specs/052-notifications-settings-extension/
├── plan.md              # Ce fichier
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/           # Phase 1 — schémas OpenAPI / messages extension
│   ├── notifications-api.md
│   ├── preferences-api.md
│   ├── account-deletion-api.md
│   ├── exports-api.md
│   └── extension-messaging.md
└── tasks.md             # Phase 2 (créé par /speckit-tasks)
```

### Source Code (repository root)

```text
backend/app/
├── notifications/                # existant — étendu
│   ├── schemas.py                #   + NotificationPreferenceIn/Out, kind enum partagé
│   ├── service.py                #   + apply_preferences, mark_all_read batch
│   └── router.py                 #   + GET/PATCH /me/notification-preferences
├── users/                        # existant — étendu
│   ├── schemas.py                #   + AccountDeletionRequestIn/Out, EmailChangeOut, SessionOut
│   ├── service.py                #   + request_account_deletion, cancel_deletion, change_email_request
│   └── router.py                 #   + DELETE /me, POST /me/cancel-deletion, GET /me/sessions, DELETE /me/sessions/{id}
├── dashboard/                    # existant — étendu
│   └── router.py                 #   + GET /me/exports (historique listing)
├── extension/                    # existant — étendu
│   ├── schemas.py                #   + ExtensionPingIn/Out, SidepanelContextOut
│   ├── service.py                #   + record_ping, build_sidepanel_context (candidatures actives + offres recommandées via matching)
│   └── router.py                 #   + POST /me/extension/ping, GET /me/extension/sidepanel-context
├── alembic/versions/             # nouvelle migration
│   └── 0XXX_f52_notification_preferences_account_deletion_extension_ping.py
└── tests/
    ├── unit/notifications/test_preferences.py
    ├── integration/users/test_account_deletion.py
    ├── integration/extension/test_sidepanel_context.py
    └── integration/dashboard/test_exports_listing.py

frontend/app/
├── pages/
│   ├── notifications/index.vue                  # remplace pages/notifications.vue (liste paginée + filtres + drawer)
│   ├── parametres/
│   │   ├── index.vue                            # vue d'ensemble + navigation latérale
│   │   ├── profil.vue                           # nom, email (re-vérif), photo, langue
│   │   ├── notifications.vue                    # toggles email/in-app par kind
│   │   ├── consents.vue                         # liste + retrait
│   │   ├── securite.vue                         # sessions actives + revoke
│   │   ├── donnees.vue                          # export RGPD complet
│   │   └── suppression.vue                      # zone dangereuse (J+30 + annulation)
│   └── dashboard/
│       └── exports.vue                          # historique + nouvelle génération
├── components/
│   ├── notifications/
│   │   ├── NotificationList.vue
│   │   ├── NotificationRow.vue
│   │   ├── NotificationFilters.vue
│   │   ├── NotificationDetailDrawer.vue
│   │   └── NotificationsEmptyState.vue
│   ├── parametres/
│   │   ├── SettingsLayout.vue                   # nav latérale partagée
│   │   ├── ProfileForm.vue
│   │   ├── EmailChangeBottomSheet.vue
│   │   ├── PasswordChangeBottomSheet.vue
│   │   ├── NotificationPreferencesGrid.vue
│   │   ├── ConsentList.vue
│   │   ├── ConsentWithdrawBottomSheet.vue
│   │   ├── SessionList.vue
│   │   ├── SessionRevokeBottomSheet.vue
│   │   ├── DataExportCard.vue
│   │   ├── AccountDeletionDangerZone.vue
│   │   └── AccountDeletionBottomSheet.vue
│   └── dashboard/
│       ├── ExportsTable.vue
│       └── NewExportBottomSheet.vue
├── stores/
│   ├── notifications.ts                         # existant — + filters, mark all read batch, drawer state
│   ├── notificationPreferences.ts               # nouveau
│   ├── consents.ts                              # nouveau
│   ├── sessions.ts                              # nouveau
│   ├── accountDeletion.ts                       # nouveau
│   └── exports.ts                               # nouveau
└── composables/
    ├── useNotificationsFilters.ts               # nouveau
    ├── useEmailChangeFlow.ts                    # nouveau
    ├── useAccountDeletion.ts                    # nouveau
    └── useExtensionStatus.ts                    # nouveau

extension/                                       # MV3 existant — étendu
├── manifest.json                                # déclare side_panel + permissions notifications (P2)
├── background.js                                # routing chrome.runtime + heartbeat ping
├── content.js                                   # détection url_pattern + injection panneau
├── sidepanel/                                   # nouveau — bundle Vite Vue 3 standalone
│   ├── index.html
│   ├── main.ts
│   ├── App.vue
│   ├── routes.ts                                # routeur léger (suivi / chat / offres)
│   ├── views/
│   │   ├── ActiveCandidaturesView.vue
│   │   ├── MiniChatView.vue                     # P2 — réutilise client REST existant
│   │   └── RecommendedOffersView.vue            # P2
│   ├── components/
│   │   ├── PanelHeader.vue
│   │   ├── CandidatureCard.vue
│   │   └── OfferCard.vue
│   └── lib/
│       ├── api.ts                               # appels JWT cookie via fetch crédentials
│       └── messaging.ts                         # wrapper chrome.runtime.sendMessage
└── vite.config.ts                               # build → extension/dist/sidepanel/, bundle gzip < 200 kB
```

**Structure Decision** :

- **Application web** : extension du tronc `frontend/app/` Nuxt 4 (domaine-par-feature, pages éclatées sous `pages/parametres/`) ; aucun monorepo nouveau. Les stores Pinia existants (`notifications.ts`, `userPreferences.ts`) sont étendus, jamais remplacés.
- **Backend** : extensions chirurgicales aux packages existants (`notifications/`, `users/`, `dashboard/`, `extension/`) — pas de nouveau package. Une seule migration Alembic regroupe les 3 nouvelles tables.
- **Extension** : conserver le squelette MV3 existant (`extension/manifest.json`, `background.js`, `content.js`, `popup.*`) et **ajouter** un bundle Vite Vue 3 standalone sous `extension/sidepanel/` ; build dédié, déclaré comme `side_panel.default_path` du manifest. La séparation popup vs sidepanel est intentionnelle (popup = login/lien rapide, sidepanel = expérience riche).

## Complexity Tracking

> Aucune violation constitutionnelle. Pas d'entrée requise.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(aucune)_ | — | — |
