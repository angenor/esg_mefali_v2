# Phase 0 — Research : F52

**Feature** : Notifications, Paramètres, Exports & Panneau d'extension
**Date** : 2026-05-05

Aucune `NEEDS CLARIFICATION` n'a été émise dans le `Technical Context`. Cette note documente les décisions structurantes et les raccordements avec l'existant.

---

## R1 — Couplage avec le centre de notifications backend (F38) déjà en place

**Decision** : la page `/notifications` consomme `GET /me/notifications` (paginé), `PATCH /me/notifications/{id}/read`, et le flux SSE `app/notifications/stream.py` via le composable existant `useNotificationsStream`. Aucune duplication. Un endpoint batch `POST /me/notifications/read-all` est ajouté côté backend pour SC-002 (mark-all-read en une opération atomique avec rollback côté UI si 5xx).

**Rationale** : éviter une cascade de PATCH unitaires (N+1 réseau, latence visible). Le store Pinia `notifications.ts` a déjà la mécanique pour pousser une mutation optimiste — il suffit de lui ajouter une action `markAllReadOptimistic()` qui retourne en arrière sur erreur.

**Alternatives considérées** : (a) boucle `Promise.all` sur PATCH unitaires côté front — refusée pour le coût réseau et l'absence d'atomicité ; (b) endpoint en query param `?ids=...` — refusé car la longueur d'URL devient ingérable au-delà de 500 notifications.

---

## R2 — Préférences de notifications par kind × canal (manquant)

**Decision** : nouvelle table `notification_preference (account_id, user_id, kind, channel, enabled, updated_at)` avec contrainte d'unicité `(user_id, kind, channel)`. `kind` réutilise l'enum partagé déjà introduit dans F38 (`deadline_j_minus_30`, `deadline_j_minus_7`, `deadline_j_minus_1`, `candidature_inactive`, `offre_recommandee`, etc.). `channel ∈ {'email', 'in_app'}`. Endpoints :

- `GET /me/notification-preferences` → liste complète (auto-création de défauts à `enabled=true` si manquants).
- `PATCH /me/notification-preferences` → batch d'overrides `{kind, channel, enabled}[]`.

Le pipeline d'envoi de notifications (`app/notifications/service.py` côté F38) consulte cette table avant émission e-mail vs in-app.

**Rationale** : matrice 2-D (kind × canal) nécessite un row-per-cell pour rester extensible (futur SMS/push) sans migration. Stockage JSONB rejeté car querying inefficient lors de l'envoi.

**Alternatives** : (a) flags booléens dans `account_user` — non extensible ; (b) JSONB dans `user_preferences` — querying lent dans le pipeline d'envoi.

---

## R3 — Suppression de compte avec délai 30 jours (workflow différé)

**Decision** : nouvelle table `account_deletion_request (id, account_id, user_id, requested_at, scheduled_for, status, reason_text, cancelled_at, executed_at)` avec `status ∈ {pending, cancelled, executed}` et `scheduled_for = requested_at + interval '30 days'`. Endpoints :

- `POST /me/account-deletion` (body : `{reason_sociale_confirmation, motif?}`) — vérifie strictement que `reason_sociale_confirmation` matche `entreprise.raison_sociale`, crée la requête, déclenche e-mail de confirmation, audit log `source_of_change=manual`.
- `DELETE /me/account-deletion/{id}` (annulation) — seul l'utilisateur owner peut annuler tant que `scheduled_for > now()`.
- `GET /me/account-deletion` — état courant (renvoie `null` si aucun pending).

Cron Alembic-séparé (job lancé par `make purge-deletions` côté ops, ou tâche planifiée backend via APScheduler/SQL trigger) : exécute les `pending` dont `scheduled_for ≤ now()`, anonymise/supprime les rows métier sous le `account_id` (cascade RLS), met `status=executed`. Hors scope de la livraison F52 stricte côté infra ; la **commande CLI** est livrée et testée intégrationment.

**Rationale** : conformité RGPD (droit à l'oubli) + UEMOA (réversibilité documentée) ; saisie raison sociale = preuve d'intention équivalente à un mot de passe sans en exiger un nouveau ; délai 30 j = standard du secteur (Apple, Google) et permet rétractation.

**Alternatives** : (a) suppression immédiate — refusée (irréversibilité, risque d'erreur catastrophique) ; (b) délai 7 j — refusé car insuffisant pour utilisateur en vacances.

---

## R4 — Sessions actives & révocation individuelle

**Decision** : la table `account_user` porte déjà `password_changed_at` (utilisé pour invalider tous les JWT antérieurs lors d'un reset). Pour la révocation **individuelle** (US5/SC critique), on s'appuie sur la table existante de **refresh tokens / sessions** introduite par F02 ; si la révocation par-session n'existe pas encore, on étend le store de sessions avec un flag `revoked_at`. Endpoints :

- `GET /me/sessions` → liste des sessions actives `(id, device_label, ip_country, user_agent_summary, created_at, last_seen_at, current=bool)`.
- `DELETE /me/sessions/{id}` → invalide la session ; la requête courante de l'utilisateur ne peut révoquer sa propre session active que via logout dédié.

**Rationale** : aligne la sécurité avec attentes utilisateurs grand public (Google, GitHub) ; invalidation côté JWT sans changer le secret global = besoin d'une table de révocation interrogée par le middleware d'auth.

**Alternatives** : (a) rotation de tous les tokens à chaque révocation — refusée (forcerait la déconnexion globale) ; (b) tokens courts uniquement — déjà la pratique mais insuffisant pour révocation immédiate.

---

## R5 — Export RGPD complet et historique

**Decision** :

- L'endpoint `GET /me/data/export` existe déjà (F32) et renvoie un JSON portable. Pour F52 on **n'introduit pas** de génération asynchrone par défaut : la taille typique d'un compte PME au MVP reste sous 100 Mo (ordres de grandeur : ~10 candidatures, ~50 documents OCR, ~30 rapports → JSON < 30 Mo + références aux fichiers).
- Si `Content-Length > 100 MB`, la réponse mute en `202 Accepted` + un job d'archivage S3-compatible (`app/storage/`) génère une signed URL valide 7 jours, livrée par e-mail.
- Nouveau endpoint `GET /me/exports` qui liste **tous les exports historiques** (rapports PDF F49 + attestations F30 + archives JSON), filtrable par type. Source : table `export_artifact (id, account_id, type, format, size_bytes, generated_at, signed_url_expires_at, status)` — soit existante (à vérifier), soit ajoutée par cette migration si manquante.

**Rationale** : un seuil dur 100 Mo + bascule e-mail couvre les cas extrêmes sans imposer une architecture asynchrone systématique au MVP. Le listing dédié évite que l'utilisateur ne re-génère des PDF déjà disponibles.

**Alternatives** : (a) tout asynchrone via Celery — refusé (over-engineering pour le MVP) ; (b) export streamé à la volée — refusé (pas de checkpoint, expérience utilisateur dégradée si déconnexion).

---

## R6 — Bundle de l'extension Chromium MV3 sidepanel

**Decision** : ajouter `extension/sidepanel/` comme **projet Vite indépendant** (non Nuxt) avec entrée `index.html` + `main.ts` montant `App.vue`. Build → `extension/dist/sidepanel/`, déclaré dans `manifest.json` :

```json
{
  "side_panel": { "default_path": "dist/sidepanel/index.html" },
  "permissions": ["sidePanel", "storage", "notifications"],
  "host_permissions": [...catalog url_patterns]
}
```

L'API `chrome.sidePanel.setOptions` (MV3 stable depuis Chrome 114) permet de n'ouvrir le panneau que sur URLs listées (action déclenchée par `content.js` après match du `url_pattern`). Pas de Vue Router complet — un mini-routeur custom (`routes.ts`) avec 3 vues (candidatures / chat / offres). `nuxt-security` n'est pas dans ce bundle ; les CSP de l'extension viennent de `manifest.json` (`script-src 'self'`, pas d'inline ni d'eval).

**Build target** : Chrome 114+ / Edge 114+ / Brave 1.55+. Firefox post-MVP (l'API `sidePanel` n'est pas encore stable côté Mozilla).

**Bundle budget** : ≤ 200 kB JS gzip. Mesuré via `vite build --mode production` + `gzip-size`. Dépendances retenues : Vue 3 + `@vue/runtime-dom` (~35 kB), tailwind compilé avec `@tailwindcss/cli` à la build (~15 kB après purge), pas de Pinia (`useState` + `provide/inject` suffisent), pas de gsap (animations CSS natives suffisantes pour P1). Mini-chat (P2) n'embarque pas le rendu Markdown lourd : un sous-set est compilé avec `marked` (~5 kB) + DOMPurify (~12 kB).

**Rationale** : un bundle Vite isolé sépare proprement le code de l'extension de l'app web (CSP différente, pas de SSR Nuxt à transpiler, ergonomie de dev plus rapide). Vue 3 + Vite est cohérent avec la stack frontend.

**Alternatives** : (a) bundle Nuxt SPA mode — refusé (overhead, polyfills inutiles, > 250 kB) ; (b) Web Components vanilla — refusé (perte d'ergonomie de dev pour un gain marginal sur les 35 kB de runtime Vue).

---

## R7 — Cloisonnement tenant ↔ extension (P2 sécurité critique)

**Decision** :

- La sidepanel s'authentifie via cookie `Secure` + `SameSite=None` partagé avec l'app web (utilisateur déjà loggé sur `app.esg-mefali.example`). L'extension **ne stocke jamais** de JWT en `chrome.storage` ni en `localStorage`.
- Les `chrome.runtime.sendMessage` de `content.js` vers `background.js` ne véhiculent **que des métadonnées non-sensibles** (URL courante, hash de pattern matché). Le payload tenant (candidatures, offres) est **toujours** récupéré par `fetch('/me/extension/sidepanel-context', { credentials: 'include' })` depuis le background — jamais transmis depuis le content-script.
- `sender.tab.url` est validé en background avant tout fetch : si l'URL ne matche aucun `url_pattern` actif côté backend, le sidepanel reçoit un état vide.

**Rationale** : éviter qu'un site malveillant injectant un faux event ne récupère des données du tenant courant. Le serveur reste l'unique source d'autorité d'authentification.

**Alternatives** : (a) JWT stocké dans `chrome.storage.local` — refusé (exfiltration possible via extension malveillante installée au même profil) ; (b) communication via `window.postMessage` côté content — refusé (interception triviale par la page hôte).

---

## R8 — Performance LCP `/notifications` < 1 s

**Decision** : SSR Nuxt 4 + cache HTTP `private, max-age=15` sur la liste paginée + `Suspense` pour le drawer de détail. Pas de virtualisation au MVP (50 lignes max par page) ; à introduire si l'utilisateur dépasse 500 notifications cumulées (déclenchement métier). Le store Pinia est hydraté SSR par le composable existant `useNotificationsStream`.

**Rationale** : avec ~50 lignes par page la table reste sous 50 kB DOM ; LCP se joue sur le TTFB backend (déjà < 200 ms p95) + premier paint Tailwind.

**Alternatives** : virtualisation `vue-virtual-scroller` — différée (over-engineering MVP).

---

## R9 — Détection extension côté `/parametres` (US9 / FR-028)

**Decision** : nouvelle table `extension_ping (account_id, user_id, version, last_ping_at, user_agent_summary)` (un row par user). L'extension envoie `POST /me/extension/ping` au démarrage du background script et toutes les 30 minutes. La page `/parametres` lit `GET /me/extension/status` (retourne `{detected: bool, last_ping_at, version}`).

**Rationale** : alternative simple et robuste à `chrome.runtime.connect` côté web (limité par le manifest et nécessite un `externally_connectable` configuré). Le ping côté backend est aussi exploitable par les analytics produit.

**Alternatives** : `externally_connectable` — refusé (besoin d'un origin whitelist par stage, fragile en dev) ; détection côté navigateur via `chrome.runtime?.id` — refusé (pas d'info de version ni de last-seen).

---

## Synthèse des dépendances

| Dépendance | Statut | Action F52 |
|------------|--------|------------|
| F36 (design system tokens) | ✅ livré | Réutilisé |
| F37 (UI primitives) | ✅ livré | Réutilisé (table, drawer, toggle, badge) |
| F38 (app shell + notifications stream) | ✅ livré | Réutilisé (store + SSE) |
| F40 (viz/Markdown) | ✅ livré | Réutilisé pour rendu mini-chat |
| F34 backend | ✅ livré | Étendu (préférences, deletion, sessions) |
| F05 (consents) | ✅ livré | UI consommée + retrait audité |
| F32 (data export) | ✅ livré | UI listing + bouton télécharger |
| F39 (bottom-sheet engine) | ✅ livré | Utilisé pour toutes saisies sensibles |
| F41 (chat conversational) | ✅ livré | Mini-chat extension réutilise client |
| F25 (matching) | ✅ livré | 3 cards offres recommandées dans extension |
| F33 (extension URL patterns) | ✅ livré | Source du `host_permissions` + matcher |

Aucune dépendance bloquante.
