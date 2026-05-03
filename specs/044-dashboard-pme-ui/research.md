# Research — F44 Dashboard PME UI

**Date** : 2026-05-03
**Status** : Phase 0 — toutes décisions prises, aucun NEEDS CLARIFICATION restant.

## R1 — Stratégie de rafraîchissement : polling 60 s vs SSE F41

**Decision** : **Polling HTTP** sur `GET /me/dashboard/summary` toutes les 60 s tant que l'onglet est focus (Page Visibility API), avec en complément l'écoute du **`useChatEventBus`** existant pour invalider/re-fetch un bloc précis dès qu'une mutation chat se produit.

**Rationale** :
- Le backend F32 expose un endpoint REST simple ; aucune route SSE n'est livrée pour le dashboard. Construire un canal SSE dédié dépasse le scope F44 (le brief le note explicitement comme P2 / "OR SSE F41").
- L'EventBus chat est déjà en place (utilisé par F43 pour la sync profil). Il sert pour les invalidations **immédiates** déclenchées par le chat ouvert dans le même onglet.
- Le polling 60 s couvre les changements opérés depuis un autre onglet, depuis l'admin, ou depuis un calcul en arrière-plan déclenché hors session. Le seuil de 90 s exigé par SC-008 / FR-017 est tenu (60 s + jitter < 90 s).
- L'usage de `document.visibilityState` évite de hammer le backend quand l'utilisatrice change d'onglet.

**Alternatives considered** :
- **SSE dédié `/me/dashboard/events`** : surdimensionné pour le MVP, demande une route backend non livrée. Reportée post-MVP.
- **Pas de polling, refresh manuel** : casse SC-008 et US8. Rejetée.
- **WebSocket** : non utilisé ailleurs dans la stack ; coût d'infrastructure injustifié.

**Implémentation** :
- `useDashboardSummary` expose `summary`, `loading`, `errorByBlock`, `refresh(block?)`.
- Setup interval 60 s dans `onMounted`, clear dans `onUnmounted`.
- Listener `visibilitychange` : pause si `hidden`, reprise immédiate au retour avec un `refresh()` fresh.
- Invalidation EventBus : à réception d'un event du tableau `EVENT_TO_BLOCK_MAP` (cf. R5), appel `refresh(block)` qui re-fetch `summary` et n'écrit que le bloc concerné dans le store (les autres restent intacts pour éviter les re-renders).

## R2 — Cohabitation `EmptyStateLanding` (F42) ↔ Dashboard 6 cartes

**Decision** : **Conserver le garde-fou existant** `pages/dashboard.vue` qui affiche `EmptyStateLanding` quand `entrepriseStore.completionPct < 50`. Au-delà de 50 %, le nouveau dashboard (six cartes) prend le relais.

**Rationale** :
- F42 a livré un parcours d'onboarding de bonne qualité : couper trop tôt vers le dashboard "vide intelligent" ferait perdre la valeur pédagogique du landing.
- Le seuil 50 % correspond grosso modo au moment où la PME a au moins une donnée chiffrée à projeter.
- Cas "compte vierge total" du spec (US3) ne correspond pas à un compte profil < 50 % mais à un compte profil ≥ 50 % SANS scoring/carbone/crédit/candidature/rapport. Dans ce cas, chaque carte est en mode "vide intelligent" (CTA d'invitation), conformément à FR-012.

**Alternatives considered** :
- **Toujours afficher le dashboard 6 cartes (suppression `EmptyStateLanding`)** : régression UX pour les nouveaux comptes. Rejetée.
- **Seuil paramétrable** : sur-ingénierie pour le MVP. Rejetée.

**Implémentation** : `pages/dashboard.vue` garde la branche conditionnelle existante ; le nouveau code est rendu dans la branche `else`.

## R3 — Mapping `DashboardSummaryOut` → ViewModels par carte

**Decision** : Une fonction pure **`mapSummaryToCardViewModels(summary, t)`** dans `lib/mapSummaryToCardViewModels.ts` qui retourne un objet typé `DashboardCardViewModels` avec une clé par carte. Cette fonction est testée unitairement (vitest) et ne dépend que de la primitive de traduction `t` injectée.

**Rationale** :
- Isole la logique de transformation (souvent verbeuse : agrégation, tri, formatage Decimal) hors des composants Vue, pour faciliter les tests.
- Permet aux composants `Card*.vue` d'être quasi-déclaratifs, donc faciles à snapshot-tester.
- Facilite la gestion uniforme des **états vides** : la fonction retourne explicitement `{ kind: 'empty', cta }` quand le bloc source est vide, ce qui élimine la branchitude conditionnelle dans le template.

**Alternatives considered** :
- **Mapping dans chaque composant carte** : duplication, tests plus lourds (montage Vue), couplage UI ↔ schéma backend. Rejeté.
- **Mapping dans le store** : confond responsabilités état / présentation. Rejeté.

## R4 — Mini-charts performance (radar 3 axes, line 4 trim, gauge 0-100)

**Decision** : Réutiliser **`components/viz/*`** existants (`VizRadarChart`, `VizLineChart`, `VizGaugeChart`) déjà livrés par F40 (basés sur chart.js). Configuration : palette compacte, labels masqués sur les mini-versions, animations désactivées côté `useReducedMotion` actif, tooltip activé.

**Rationale** :
- Pas de nouvelle dépendance graphique.
- chart.js est déjà chargé par F40 — pas de surcoût bundle.
- Les mini-charts dans des cartes de ~250 px de haut nécessitent juste de réduire la densité (axes/labels) ; pas de nouvelle implémentation graphique.

**Alternatives considered** :
- **SVG pur "à la main"** pour la légèreté : duplication d'effort vs chart.js déjà en place. Rejeté.
- **D3** : non utilisé ailleurs, surcoût injustifié. Rejeté.

**Implémentation** : créer une variante `compact` (prop) sur les composants viz si elle n'existe pas déjà ; sinon passer les options via props existantes.

## R5 — Cartographie events chat ↔ blocs dashboard

**Decision** : Table `EVENT_TO_BLOCK_MAP` codée dans `useDashboardSummary` (ou exposée par `lib/dashboardEventMap.ts`) :

| Event chat (nom) | Bloc summary à invalider |
|------------------|--------------------------|
| `scoring:computed` | `scores` |
| `carbon:computed` | `carbon` |
| `credit:computed` | `credit_score` |
| `candidature:status_changed` | `candidatures` |
| `candidature:created` | `candidatures` |
| `rapport:generated` | `rapports` |
| `attestation:emitted` | `attestations` |
| `action_step:completed` | `next_actions` |
| `action_step:created` | `next_actions` |

**Rationale** :
- Liste explicite, facile à amender, testable unitairement.
- Évite un re-fetch global pour chaque event (perf + audit pollution).
- Cohérent avec le wiring déjà en place dans F43 (sync profil) qui suit le même pattern.

**Note** : si un event arrive et qu'aucune entrée n'existe dans la map → ignoré (pas d'erreur). Si l'event correspond à un mutation déclenchée localement par le dashboard (cocher étape), le re-fetch est évité (idempotence : l'optimistic update est déjà appliqué).

## R6 — Format de fichier d'export

**Decision** : **JSON** (étendre `application/json`), nommé `esg-mefali-export-YYYY-MM-DD.json`. Pas d'autre format au MVP.

**Rationale** :
- C'est exactement ce que retourne `GET /me/data/export` (schema `DataExportOut`).
- RGPD art. 20 (portabilité) exige un format "structuré, couramment utilisé et lisible par machine" — JSON satisfait cette exigence.
- ZIP / CSV demandent une couche d'archivage côté backend non livrée par F32. Hors-scope MVP.

**Alternatives considered** :
- **ZIP avec CSV par table** : confort utilisateur supérieur, mais nécessite extension F32. Reporté post-MVP.
- **PDF** : non portable (RGPD), non lisible machine. Rejeté.

**Implémentation** : `useDataExport` :
1. fetch `/me/data/export` avec header `Accept: application/json` ;
2. construit un `Blob` JSON ;
3. crée un `<a download>` programmatique avec `URL.createObjectURL` ;
4. désactive le bouton pendant la requête + 2 s post-download (anti double-clic FR-021) ;
5. nomme le fichier via `Intl.DateTimeFormat('fr-CA')` (format ISO `YYYY-MM-DD`).

## R7 — Affichage QR code des attestations

**Decision** : Réutiliser **`<VizSourcePin>`** ? **Non** — `VizSourcePin` est dédié au sourçage. Pour les QR mini, utiliser **`qrcode.vue`** (≈ 4 ko) ou la déjà-installée bibliothèque QR si présente. Vérifier `package.json` ; sinon ajouter `qrcode-vue3` (mainstream, < 10 ko, pas de dépendance lourde).

**Rationale** :
- Le QR de la carte attestation n'a pas vocation à être scanné depuis le dashboard (résolution insuffisante) ; il sert d'**affordance visuelle** rappelant qu'une attestation est vérifiable. Le clic ouvre la page de vérification publique `/verify/{public_id}` (F30/F52).
- À défaut de bibliothèque, placeholder SVG statique cliquable est acceptable au premier jet (T0 du wizard `/speckit-tasks`).

**Implémentation** : `CardRapports.vue` rend chaque attestation comme un mini-bouton 48×48 px contenant un QR généré, lien `<NuxtLink to="/verify/{public_id}">`.

## R8 — Carte "Intermédiaires recommandés" (P2)

**Decision** : Carte rendue **conditionnellement** : visible uniquement si la PME a un profil ≥ 50 % ET au moins un projet ET au moins un match calculé par F25. Sinon masquée (la grille passe de 7 à 6 cartes).

**Rationale** :
- Pas de valeur d'afficher une carte vide d'intermédiaires.
- F25 (matching) expose déjà `/me/matching/recommendations?limit=3`. À fetch en lazy depuis `CardIntermediaires.vue` (pas dans `summary` qui ne l'inclut pas en F32).

**Alternatives considered** :
- **Inclusion dans `summary`** : implique modifier F32. Hors scope F44.
- **Pré-fetch systématique** : coût réseau pour rien si la PME n'a pas de projet.

**Implémentation** : `CardIntermediaires.vue` fait son propre fetch via `useFetch('/me/matching/recommendations?limit=3')` au mount, avec garde-fou `v-if="hasProjet"` géré par le parent.

## R9 — Squelettes et perf LCP

**Decision** : SSR rend les **squelettes** (sans données), puis l'hydratation déclenche `useDashboardSummary().refresh()` côté client.

**Rationale** :
- LCP < 1,5 s p95 (SC-001) atteignable seulement si la première peinture n'attend pas le réseau.
- Les squelettes sont des `<div>` Tailwind simples ; coût de rendu négligeable.
- L'hydratation Nuxt 4 garantit que le polling démarre dès `onMounted`.

**Alternatives considered** :
- **SSR avec data réelle** (`useFetch` côté serveur) : meilleur LCP visuel mais nécessite le cookie JWT côté serveur. Possible avec la session middleware existante ; à activer si SC-001 n'est pas tenu en CR. Marqué comme amélioration optionnelle T0+ (`tasks.md`).

## R10 — Localisation des libellés

**Decision** : Toutes les chaînes ajoutées passent par `useT()` et sont stockées dans `frontend/app/locales/fr.ts` sous le namespace `dashboard.*`.

**Rationale** :
- Cohérence avec F38/F42/F43.
- Facilite l'arrivée future de l'EN pour dossiers anglophones (constitution).

## Récapitulatif des décisions

| ID | Décision |
|----|----------|
| R1 | Polling 60 s + visibility API + EventBus invalidation ciblée. |
| R2 | Conserver `EmptyStateLanding` < 50 % completion. |
| R3 | Adapter pur `mapSummaryToCardViewModels` testé unitairement. |
| R4 | Réutiliser `components/viz/*` existants (chart.js). |
| R5 | Map événements chat → blocs explicite. |
| R6 | Export JSON uniquement, nommé `esg-mefali-export-YYYY-MM-DD.json`. |
| R7 | QR mini via lib légère ; clic vers `/verify/{public_id}`. |
| R8 | Carte intermédiaires masquée si pas de projet ; lazy-fetch propre. |
| R9 | SSR squelettes + hydratation déclenche fetch. |
| R10 | i18n via `useT` + `locales/fr.ts` namespace `dashboard.*`. |
