# Extension Chrome ESG Mefali

Extension MV3 (Chrome / Edge / Brave) qui détecte les URLs de plateformes
financières au catalogue (F33), pré-remplit certains champs (F33 US4/US5)
et — depuis F52 — affiche un panneau latéral riche (`chrome.sidePanel`)
avec les candidatures actives, un mini-chat IA contextuel et 3 offres
recommandées.

## Installation locale (mode unpacked)

1. Lancer le backend FastAPI : `make backend` → `http://localhost:8010`.
2. Lancer le frontend Nuxt : `make frontend` → `http://localhost:3001`.
3. Builder le sidepanel : `pnpm --dir extension build:sidepanel`
   (sortie : `extension/dist/sidepanel/`).
4. Ouvrir `chrome://extensions`, activer **Mode développeur**.
5. Cliquer **Charger l'extension non empaquetée** et sélectionner le dossier
   `extension/`.
6. Cliquer l'icône de l'extension dans la barre Chrome → popup → saisir
   l'email/mot de passe d'un compte PME ESG Mefali.

## Structure

```text
extension/
├── manifest.json           # Permissions + side_panel + content_scripts
├── background.js           # Service worker MV3 (auth, ping, sidepanel, SSE)
├── content.js              # Détection url_pattern dans la page hôte
├── popup.{html,css,js}     # Login rapide
├── background-helpers/
│   └── notifications.ts    # Wrapper testable autour de chrome.notifications
├── sidepanel/              # Bundle Vite Vue 3 standalone
│   ├── App.vue
│   ├── routes.ts           # candidatures | offers | chat
│   ├── components/         # PanelHeader, CandidatureCard, OfferCard
│   ├── views/              # Active/Recommended/MiniChat
│   ├── lib/                # api.ts (REST), messaging.ts (chrome.runtime)
│   └── __tests__/          # Vitest + happy-dom
└── scripts/check-bundle-size.mjs  # garde-fou < 200 kB gzip
```

## Backend URL

Par défaut `http://localhost:8010`. Pour pointer ailleurs (préprod, prod EU),
mettre à jour la constante `BACKEND` dans `popup.js`, `background.js`,
`content.js`, ainsi que les `host_permissions` du `manifest.json`.

## Notifications système (P2)

L'extension peut émettre des **notifications natives** lorsqu'une candidature
arrive à échéance dans moins de 24 h (kind `deadline_j_minus_1`). Le
mécanisme :

1. Le service worker ouvre une connexion **SSE** vers
   `/me/notifications/stream` dès que l'utilisateur est authentifié
   (cookie httpOnly partagé avec l'app web).
2. Sur l'événement `notification.created` de kind `deadline_j_minus_1`,
   le wrapper `background-helpers/notifications.ts` (testé via Vitest)
   appelle `chrome.notifications.create` avec `priority: 2`, l'icône
   d'extension et le titre/corps du payload (avec fallback FR par défaut).
3. Le clic ouvre le `link` du payload dans un nouvel onglet
   (`chrome.tabs.create`). Un seul listener `chrome.notifications.onClicked`
   est installé : les liens sont gérés via une `Map` (id → url) pour éviter
   les fuites mémoire de listeners multiples.

### Opt-in OS

Les notifications système requièrent l'autorisation **du navigateur** *et*
**du système d'exploitation** :

- **Chrome / Edge / Brave** : `Paramètres` → `Confidentialité et sécurité`
  → `Paramètres des sites` → `Notifications` → activer pour
  `chrome-extension://<id>` (ou via la pop-up native au premier déclenchement).
- **macOS 12+** : `Réglages Système` → `Notifications` → sélectionner le
  navigateur → `Autoriser les notifications`.
- **Windows 11** : `Paramètres` → `Système` → `Notifications` → activer pour
  le navigateur.
- **GNU/Linux (KDE/GNOME)** : `Paramètres` → `Notifications` → autoriser le
  navigateur correspondant.

### Révocation

L'utilisateur peut révoquer l'autorisation à tout moment via les mêmes
écrans OS / navigateur. ESG Mefali **n'envoie aucune notification système
de re-prompt** : si l'opt-in est refusé, les rappels in-app
(`/notifications`) et e-mail (préférences `/parametres/notifications`)
restent les canaux principaux. Aucune fonctionnalité critique de
l'extension ne dépend de ce canal.

### Cloisonnement (P2)

- L'EventSource utilise `withCredentials: true` ; aucune information
  cross-tenant ne peut transiter.
- Les payloads SSE n'embarquent jamais d'identifiant tenant : le `link`
  pointe sur `https://app.esg-mefali.example/candidatures/<id>` avec
  vérification serveur RLS.
- Le mock cli d'évaluation est fourni dans
  `frontend/e2e/052/extension-tenant-isolation.spec.ts`.

## Tests

- **Vitest** (sidepanel + helpers) :
  `pnpm --dir extension exec vitest run --config sidepanel/vite.config.ts`
- **E2E Playwright** (frontend mock BOAD) :
  `frontend/e2e/052/extension-sidepanel.spec.ts` (squelette, exécution
  conditionnée par `E2E_RUN_EXTENSION=1`).

## Endpoints utilisés

- `POST /auth/login`
- `GET /extension/profile-summary`, `/extension/url-patterns`,
  `/extension/field-mappings`, `POST /extension/suggest-field`
- `POST /me/extension/ping`
- `GET /me/extension/status`
- `GET /me/extension/sidepanel-context`
- `GET /me/notifications/stream` (SSE — `notification.created`,
  `notification.bulk_read`, `notification.read`)

## Limites MVP / hors scope

- Firefox post-MVP (manifest MV3 partiel sur Firefox 128+).
- Pas de notifications push web (FCM) : SSE + `chrome.notifications` au MVP.
- Mini-chat extension : les saisies passent par un bottom-sheet (P10) ;
  pas de Markdown lourd, pas d'upload fichier dans cette surface.
