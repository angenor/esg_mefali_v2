# F45 — Plan d'action ESG UI (UI de F31)

**Phase** : D — Tableaux de bord & visualisations métier
**Modules brainstorm** : 5.2 plan d'action
**Dépendances** : F36, F37, F38, F39, F31 backend, F23 scoring, F47 visualisations scoring
**Estimation** : 2.5 jours

## Contexte et objectif

Page **`/plan-action`** : la PME visualise sa feuille de route ESG, coche l'avancement, filtre par priorité/horizon/responsable. Sortie qui donne **envie de progresser** : timeline horizontal sobre + cards triables.

## User Stories

- **US1 Vue timeline (P1)** — timeline horizontale (gsap reveal scroll) ponctuée par horizon (3/6/12/24 mois), couleur priorité, hover = title.
- **US2 Vue liste avec filtres (P1)** — filtres priorité, statut, horizon, responsable. Tri par défaut priorité+horizon.
- **US3 Card étape (P1)** — titre, description, priorité, horizon (date), status (chip), responsable (avatar), source du gap (lien indicateur). Bouton "Modifier statut".
- **US4 Drawer édition statut (P1)** — bottom sheet F39 (status + responsable_user_id) → `PATCH /me/action-plan/steps/{id}` → refresh card.
- **US5 Bouton "Régénérer mon plan" (P1)** — modal confirmation → `POST /me/action-plan/generate?horizon=12`.
- **US6 Selecteur horizon (P1)** — toggle `6 / 12 / 24 mois`.
- **US7 Empty state pas de score (P1)** — "Lancez votre scoring ESG d'abord" + CTA `/scoring`.
- **US8 Empty state pas de gaps (P1)** — célébration sobre "Excellent ! Aucune action prioritaire détectée."
- **US9 Indicateur progression (P1)** — barre globale `done / total` + KPI "Avancement : X %".
- **US10 Sync chat (P1)** — `useChatEventBus` listen `entity_updated{action_step}` → refresh card (P8).
- **US11 Historique versions (P2)** — drawer plans antérieurs lecture seule.
- **US12 Export PDF (P2)** — bouton "Exporter en PDF" → backend F51.

## Exigences fonctionnelles

- **FR-001** : `pages/plan-action/index.vue` + `components/plan-action/{TimelineHorizontal,StepCard,EditStatusSheet,RegenerateModal}.vue`.
- **FR-002** : Pinia `useActionPlanStore` (currentPlan, version, steps, filters).
- **FR-003** : Timeline horizontal SVG ou divs flexbox + gsap stagger 80 ms.
- **FR-004** : Edit drawer = `<ChatBottomSheet>` F39 + `<ShowForm>`.
- **FR-005** : Filtres dans URL query (`?priority=haute&status=todo`).
- **FR-006** : `useActionPlanCompletion()` calcule % done / total.
- **FR-007** : Cocher rapide carte : checkbox optimiste, rollback si PATCH échoue.

## Exigences non-fonctionnelles

- **NFR-001** : LCP < 1.5 s avec 50 étapes.
- **NFR-002** : Filtrage client < 50 ms pour 100 étapes.
- **NFR-003** : Animations stagger respectent `prefers-reduced-motion`.

## Success Criteria

- **SC-001** : Générer plan, voir 5+ étapes timeline + liste < 2 s.
- **SC-002** : Modifier statut "doing" → refresh + progress update.
- **SC-003** : Filtrer "priorité haute" → seulement étapes haute.
- **SC-004** : Régénérer → version v+1, ancien accessible historique (P2).

## Hors-scope MVP

- Drag réordonner (priorités algorithmiques) → post-MVP.
- Notif email échéance → DEFERRED F31.
- Reco contextuelle bibliothèque → DEFERRED F31.
- Calendrier externe ICS → post-MVP.

## Risques et points de vigilance

- Cocher optimiste : rollback propre si réseau fail.
- Timeline mobile : passer en vertical < 768 px.
- Régénérer : warning destructif clair.
- Filtres URL : ne pas péter SSR si query invalide.
