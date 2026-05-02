# F48 — Credit scoring UI (UI de F29)

**Phase** : D — Tableaux de bord & visualisations métier
**Modules brainstorm** : 3.3 credit scoring
**Dépendances** : F36, F37, F38, F39, F40, F29 backend (credit_data, credit_score)
**Estimation** : 2 jours

## Contexte et objectif

Page **`/credit-score`** : score crédit (0-100), décomposition (sous-scores), éligibilités (BOAD, SUNREF, Ecobank Green Lending), recommandations actionnables.

Style : gauge centrale visible, sous-scores en cards, badges éligibilité prominents.

## User Stories

- **US1 Vue synthèse (P1)** — `<VizGaugeChart>` 0-100 + classification (Excellent / Bon / À améliorer / Insuffisant) + KPI "Évolution N-1" delta.
- **US2 Décomposition sous-scores (P1)** — 4 cartes : Solidité financière, Performance opérationnelle, Engagement ESG, Gouvernance. Sous-score + barre.
- **US3 Badges d'éligibilité (P1)** — "Vous êtes éligible à" : BOAD-vert, SUNREF, Ecobank Green Lending. Click → modal conditions + lien matching F53.
- **US4 Recommandations (P1)** — 3-5 actions priorisées issues plan F45 ; impact estimé "+X points".
- **US5 Saisie data financière (P1)** — `<ChatBottomSheet show_form>` F39 multi-étapes (CA, EBE, dette, fonds propres). Money typé (P5).
- **US6 Recalcul automatique (P1)** — submit → `POST /me/credit-score/calculate` → gauge animée gsap + toast "+8 points".
- **US7 Historique score (P1)** — `<VizLineChart>` 6 derniers calculs.
- **US8 Empty state (P1)** — wizard 4 étapes (CA, dette, ESG, gouvernance).
- **US9 Sync chat (P1)** — `useChatEventBus` listen `entity_updated{credit_data,credit_score}` → refresh.
- **US10 Export rapport (P2)** — F51.

## Exigences fonctionnelles

- **FR-001** : `pages/credit-score/index.vue` + `components/credit/{GaugeHero,SubScoreCard,EligibilityBadge,RecommendationList}.vue`.
- **FR-002** : Pinia `useCreditStore`.
- **FR-003** : Gauge animée gsap : tween ancien → nouveau score (320 ms).
- **FR-004** : Money : `decimal.js` côté client, `<UiNumber money>` F37.
- **FR-005** : Recommandations cliquables → `/plan-action#step-{id}`.
- **FR-006** : Eligibility badges → `<UiModal>` détail conditions.

## Exigences non-fonctionnelles

- **NFR-001** : LCP < 1.5 s.
- **NFR-002** : Wizard 4 étapes < 3 min sur mobile.
- **NFR-003** : Gauge animation 60 fps.

## Success Criteria

- **SC-001** : Score 72 → gauge + classification "Bon".
- **SC-002** : Saisir nouveau CA → recalcul + animation fluide.
- **SC-003** : Badge "BOAD-vert" cliqué → modal conditions.
- **SC-004** : Recommandation cliquée → `/plan-action`.

## Hors-scope MVP

- Benchmark sectoriel → post-MVP.
- Simulation "Si X alors Y" → couvert F55 simulateur.
- Notation Bâle III détaillée → post-MVP.

## Risques et points de vigilance

- Score crédit = data sensible : audit F04 systématique.
- Money precision : jamais Number, toujours decimal.
- Gauge color-blind friendly : texte + couleur.
- Impact estimé recommandation : marquer "estimation" claire.
