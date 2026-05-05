# Quickstart — App Shell, Layout & Navigation (F38)

## Prérequis

- Backend FastAPI déjà lancé sur `:8010` (cf. `CLAUDE.md`).
- Postgres dockerisé (`make db-up`) avec migrations à jour (`make migrate`).
- Frontend Nuxt 4 en `pnpm dev` (port 3001).
- Compte PME stub déjà créé via `/auth/register` (sinon l'inscription est dispo en `/register`).

## Démarrer

```bash
# 3 terminaux
make db-up
make backend            # FastAPI :8010 (inclut le stub SSE /me/events)
make frontend           # Nuxt :3001
```

Ouvrir `http://localhost:3001`.

## Smoke-tests manuels

### S-001 — Pages publiques

1. En navigation privée, ouvrir `http://localhost:3001/login`.
   ✓ Layout split-screen visible sur ≥ 1024 px (illustration à gauche, formulaire à droite).
   ✓ Pas de sidebar PME, pas de top-bar applicative.
2. Ouvrir `http://localhost:3001/verify/abc123` (id arbitraire).
   ✓ Header minimal (logo) + footer mentions légales, sans sidebar.

### S-002 — Squelette PME

1. Se connecter avec un compte PME.
   ✓ Redirection automatique vers `/dashboard`.
2. Observer la sidebar à gauche : 11 rubriques visibles.
   ✓ « Tableau de bord » est en état actif.
3. Cliquer sur « Profil entreprise », « Projets », « Scoring ESG ».
   ✓ Le contenu change sans rechargement complet.
   ✓ Le breadcrumb se met à jour (ex : « Accueil / Scoring ESG »).
   ✓ La barre de progression brand-500 apparaît brièvement en haut.
4. Vérifier le menu avatar.
   ✓ Affiche raison sociale + email.
   ✓ FR sélectionné, EN désactivé.

### S-003 — Palette de commandes

1. Sur n'importe quelle page PME, presser `Cmd+K` (macOS) ou `Ctrl+K` (Win/Linux).
   ✓ Palette ouverte, champ recherche focus.
2. Taper « scoring » puis ↵.
   ✓ Navigation vers `/scoring`.
3. Presser `/` puis `Esc`.
   ✓ Palette ouvre puis se ferme proprement.

### S-004 — Responsive mobile

1. Réduire la fenêtre à 360 × 800.
   ✓ Sidebar disparue, bouton hamburger visible dans le header.
   ✓ Bottom-nav avec 4 icônes en bas.
2. Cliquer sur le hamburger.
   ✓ Drawer s'ouvre avec overlay sombre.
3. Cliquer sur l'icône « Plus » de la bottom-nav.
   ✓ Sheet liste les rubriques restantes.

### S-005 — Routes protégées

1. Se déconnecter.
2. Tenter d'accéder à `http://localhost:3001/dashboard`.
   ✓ Redirection vers `/login?redirect=/dashboard`.
3. Se reconnecter.
   ✓ Redirection vers `/dashboard` (destination préservée).
4. Tenter `/admin/sources` avec un compte PME.
   ✓ Redirection vers `/dashboard`.

### S-006 — Notifications temps réel (stub)

> Le stub F38 n'émet que des keepalives ; pas d'événement métier réel
> tant que F41 n'est pas livré. On valide donc uniquement la mécanique.

1. Ouvrir DevTools → Network → filtre EventStream.
   ✓ Un appel à `/me/events` est en `pending` avec messages `event: ping` toutes les 30 s.
2. Insérer manuellement une notification en base (psql) :
   ```sql
   INSERT INTO notifications (id, account_id, kind, title, body, created_at)
   VALUES (gen_random_uuid(), '<your-account-id>', 'system', 'Test', 'Hello', now());
   ```
3. Recharger la cloche : le compteur reflète la nouvelle notif (chargée par `loadInitial` au mount + polling 60 s).
4. Cliquer sur la cloche → popover affiche la notif → cliquer dessus → `read_at` est mis à jour.

### S-007 — Hors-ligne

1. Sur une page PME, dans DevTools → Network, basculer en « Offline ».
   ✓ Bannière jaune « Connexion perdue. … » apparaît en haut.
2. Repasser « Online ».
   ✓ La bannière disparaît.

### S-008 — ErrorBoundary

1. Forcer une erreur depuis la console : `throw new Error('boom')` dans un onMount d'une page de test (`pages/dev/error.vue` à créer en local).
   ✓ Page de repli avec « Une erreur est survenue » + bouton « Recharger ».
2. Cliquer « Recharger ».
   ✓ La page se réinitialise.

### S-009 — Reduce motion

1. macOS → Préférences → Accessibilité → Réduire les animations (ou via DevTools → Rendering → Emulate CSS prefers-reduced-motion: reduce).
2. Naviguer entre 2 pages.
   ✓ Pas d'animation slide (la barre de progression reste, mais sans easing).
3. Ouvrir la palette.
   ✓ Apparition immédiate (pas de fade).

## Tests automatisés

```bash
# Frontend — vitest unitaires
cd frontend && pnpm vitest run tests/unit/shell tests/unit/composables tests/unit/stores tests/unit/middleware

# Backend — stub SSE
cd backend && source .venv/bin/activate
pytest tests/notifications/test_stream.py -v
```

Cible de couverture : ≥ 80 % sur le code ajouté (vitest `--coverage`).

## Critères d'acceptation finaux

| Critère | Méthode |
|---|---|
| SC-001 nav 5 rubriques < 10 s | manuel S-002 |
| SC-002 transition < 100 ms (95 %) | DevTools Performance + 20 navigations |
| SC-003 routes privées 100 % protégées | S-005 sur 5 routes |
| SC-004 routes publiques 100 % accessibles | S-001 sur 5 routes publiques |
| SC-005 bascule mobile | S-004 sur 360 / 412 / 768 px |
| SC-006 palette < 200 ms ouverture | DevTools Performance |
| SC-007 notif < 2 s | S-006 + INSERT côté SQL pendant que la page est ouverte |
| SC-008 logout efface session | S-005 + DevTools Application → Cookies |
| SC-009 cibles tactiles ≥ 44×44 | Inspecteur DOM, mesure box-model |
| SC-010 0 régression visuelle | screenshot avant/après refacto |

## Dépendances et ordre de livraison

- F02 (Auth) — livré ✅
- F36 (Design tokens) — livré ✅
- F37 (Primitives UI) — livré ✅
- F34 (Notifications backend) — livré ✅
- F41 (SSE événements métier) — non livré ; F38 expose un stub keepalive compatible. À l'arrivée de F41, seul `notifications/stream.py` est étendu, le contrat reste identique.
