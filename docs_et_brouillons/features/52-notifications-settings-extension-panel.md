# F52 — Notifications + Settings + Exports + Extension panneau (UI de F34/F05/F32)

**Phase** : G — Notifications, settings, extension panneau
**Modules brainstorm** : 6.0 notifications + 6.1 paramètres + 6.2 exports + 7.0 extension panel
**Dépendances** : F36, F37, F38, F40, F34 backend, F05 (consents), F32 (export listing)
**Estimation** : 4 jours

## Contexte et objectif

Quatre surfaces complémentaires regroupées (réglages secondaires) :

1. **`/notifications`** — centre des notifications (deadlines candidatures, candidatures inactives, offres recommandées).
2. **`/parametres`** — préférences user, gestion compte, consents RGPD (F05), export RGPD complet.
3. **`/dashboard/exports`** — historique exports PDF/JSON.
4. **Extension Chrome side panel** — slide-in droit : suivi candidatures actives, mini-chat IA contextuel, offres recommandées sur le site visité.

## User Stories

### `/notifications`

- **US1 Liste paginée (P1)** — table : kind (badge), title, body, read_at, created_at. Filtres : non-lues, kind, plage date.
- **US2 Mark all read (P1)** — batch `PATCH /me/notifications/{id}/read`.
- **US3 Click row → détail (P1)** — drawer body complet, action contextuelle.
- **US4 Empty state (P1)** — illustration + "Aucune notification".

### `/parametres`

- **US5 Profil utilisateur (P1)** — nom, email (modifiable + re-vérif), photo, langue. Bouton "Changer mot de passe".
- **US6 Préférences notifications (P1)** — toggles email + in-app par kind (deadline_j_minus_30/7/1, candidature_inactive, offre_recommandee).
- **US7 Consents RGPD (P1)** — F05 : liste consents avec date, "Retirer", liens politique + DPO.
- **US8 Sécurité (P1)** — sessions actives + revoke individuel, 2FA (P2 différé).
- **US9 Connecté (P2)** — extension Chrome détectée, dernier ping, "Synchroniser maintenant".
- **US10 Export RGPD complet (P1)** — "Télécharger toutes mes données" → `GET /me/data/export` (F32) JSON.
- **US11 Suppression compte (P1)** — "Zone dangereuse", confirm modal + saisie raison sociale + délai 30 j.

### `/dashboard/exports`

- **US12 Liste exports (P1)** — table : type (PDF/JSON), date, taille, signed URL temporaire.
- **US13 Génération nouvelle (P1)** — modal type + format, async + lien quand prêt.

### Extension Chrome side panel

- **US14 Panel slide-in (P1)** — détecte URL listée (F33 url_pattern), panel slide-in droite sticky scroll. Header logo + close.
- **US15 Suivi candidatures actives (P1)** — liste compacte deadline + % complétion + "Reprendre".
- **US16 Mini-chat IA (P2)** — embed simplifié F41 pour aide contextuelle.
- **US17 Offres recommandées (P2)** — 3 cards F25 compatibles, click → `/matching` nouvel onglet.
- **US18 Notifications push (P2)** — `chrome.notifications` deadline < 24h, click → `/candidatures/[id]`.

## Exigences fonctionnelles

- **FR-001** : `pages/notifications/index.vue, pages/parametres/{index,profil,securite,consents,exports}.vue, pages/dashboard/exports.vue`.
- **FR-002** : Composants `components/notifications/*, components/parametres/*`.
- **FR-003** : Extension : `extension/sidepanel/{App.vue,routes.ts}` Vue 3 standalone, build Vite séparé, bundle < 200 kB.
- **FR-004** : Pinia `useNotificationsStore, usePreferencesStore, useConsentsStore`.
- **FR-005** : Notifications panel listen SSE F38 → push count + nouvelle ligne top.
- **FR-006** : Suppression compte : workflow async backend (`delete_at = now() + 30 j`, cron purge).
- **FR-007** : Side panel ↔ page web via `chrome.runtime.sendMessage` + content scripts.

## Exigences non-fonctionnelles

- **NFR-001** : `/notifications` LCP < 1 s.
- **NFR-002** : Side panel < 200 kB JS, charge < 500 ms.
- **NFR-003** : Actions sensibles (delete, retrait consent) audit log F04.
- **NFR-004** : Side panel responsive 350-450 px.

## Success Criteria

- **SC-001** : Mark 10 notifs read batch → toutes maj, badge cloche 0.
- **SC-002** : Modifier email → re-vérification, statut "en attente".
- **SC-003** : Retirer consent F05 → audit + email confirmation.
- **SC-004** : Suppression compte → modal confirm + délai 30 j + email notification.
- **SC-005** : Side panel affiche 2 candidatures actives sur URL test BOAD.

## Hors-scope MVP

- Notifications SMS / WhatsApp → post-MVP.
- 2FA → P2.
- Push extension `chrome.notifications` natif → P2 (P7 trop de canaux).
- Side panel Firefox → MVP Chrome/Edge/Brave.
- Webhooks PME custom (Slack) → post-MVP.

## Risques et points de vigilance

- Suppression compte irréversible : workflow clair + email confirmation.
- Consents RGPD : textes DPO validés, traçabilité auditée.
- Side panel : pas de leak tenant via `runtime.sendMessage`.
- Notifications batch read : optimistic UI + rollback si fail.
- Export RGPD taille : limite 100 MB, sinon notification + email.
