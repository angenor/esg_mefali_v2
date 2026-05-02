# F44 — Dashboard PME UI (UI de F32)

**Phase** : D — Tableaux de bord & visualisations métier
**Modules brainstorm** : 4.0 dashboard
**Dépendances** : F36, F37, F38, F40, F32 backend (`/me/dashboard/summary`, `/me/data/export`)
**Estimation** : 3 jours

## Contexte et objectif

Page d'accueil PME post-login. Vue 360° **lisible en 5 secondes** : où j'en suis (scoring, carbone, crédit), ce que je dois faire (next actions plan d'action F46), où sont mes candidatures, attestations actives, accès rapide au chat.

Style : grille de cartes sobres, **max 6 cartes principales above-the-fold**, hiérarchie visuelle nette. Pas de "wall of charts". Cartes cliquables vers la page détail.

## User Stories

- **US1 Welcome strip (P1)** — bandeau haut : salutation, raison sociale, date dernier scoring, bouton "Discuter avec l'IA" prominent (deeplink `/chat`).
- **US2 Carte scores ESG (P1)** — `<VizKPICard>` score global + mini-radar 3 axes + dernière maj. Click → `/scoring` F47.
- **US3 Carte empreinte carbone (P1)** — KPI `tCO2e` total annuel + mini line-chart 4 derniers trimestres. Click → `/carbone` F48.
- **US4 Carte score crédit (P1)** — gauge 0-100 + badge "Éligible BOAD/SUNREF". Click → `/credit-score` F49.
- **US5 Carte candidatures (P1)** — compteurs par statut, liste 3 dernières. Click → `/candidatures`.
- **US6 Carte rapports & attestations (P1)** — 3 derniers rapports PDF (F51) + 2 attestations actives QR mini (F52). Click → `/rapports`.
- **US7 Carte plan d'action (P1)** — 3 prochaines étapes priorité haute, checkbox cocher → `PATCH /me/action-plan/steps/{id}`. Click → `/plan-action` F46.
- **US8 Carte intermédiaires recommandés (P2)** — mini Leaflet map (F40), 3 pins fonds/banques. Click → `/matching` F53.
- **US9 Bouton export données (P1)** — top-right "Exporter mes données" → `GET /me/data/export` (F32) → download JSON.
- **US10 État vide intelligent (P1)** — scoring jamais lancé → carte "Lancez votre premier diagnostic ESG" + CTA.
- **US11 Refresh polling (P2)** — composable `useDashboardSummary()` polling 60 s OR SSE F41.
- **US12 Skeleton loading (P1)** — chaque carte skeleton shimmer pendant fetch ; jamais "blank screen".

## Exigences fonctionnelles

- **FR-001** : `pages/dashboard/index.vue` + `components/dashboard/{Card*,WelcomeStrip}.vue`.
- **FR-002** : Pinia `useDashboardStore` cache `summary` 60 s.
- **FR-003** : Grid responsive : 3 col desktop, 2 tablet, 1 mobile.
- **FR-004** : Export JSON download `<a download>`, nom `esg-mefali-export-YYYY-MM-DD.json`.
- **FR-005** : Cartes affichent badge `(source)` cliquable F40 quand données ESG.
- **FR-006** : Empty state per-card : `scores=[]` → mini-CTA "Lancer scoring".
- **FR-007** : Page `/dashboard/exports` listant exports PDF passés (F51).

## Exigences non-fonctionnelles

- **NFR-001** : LCP < 1.5 s avec data réelle (SSR hydrate cache).
- **NFR-002** : Mobile cartes empilées, scroll 60 fps.
- **NFR-003** : Aucune carte > 200 lignes Vue.

## Success Criteria

- **SC-001** : 6 cartes affichées au load < 1.5 s LCP.
- **SC-002** : Click carte scoring → navigate, transition fluide.
- **SC-003** : Cocher étape plan d'action → mutation backend + refresh carte.
- **SC-004** : Export JSON download fonctionne.

## Hors-scope MVP

- Carte commentaires équipe → P2 multi-utilisateur.
- Drag-reorder cartes → post-MVP.
- Widgets custom → post-MVP.
- Vue admin → F10 `/admin`.

## Risques et points de vigilance

- Surcharge : limiter 6 cartes above-the-fold.
- Carte vide : CTA, jamais juste "0".
- Refresh : 60 s, ne pas hammer backend.
