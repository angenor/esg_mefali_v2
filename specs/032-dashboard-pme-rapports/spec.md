# Feature 32 — Dashboard PME (scores, candidatures, rapports, audit log, "Mes données", multi-utilisateurs)

**Branch**: `032-dashboard-pme-rapports`
**Phase**: 10 — Tableau de Bord PME (Module 7)
**Source brouillon**: `docs_et_brouillons/features/32-dashboard-pme-rapports.md`
**Dépendances** : F04 (audit), F05 (privacy), F23 (scoring), F24 (rapports), F25 (matching), F30 (attestations), F31 (action plan).

## Scope MVP livré (P1 backend agrégateur)

Cette feature livre — en backend uniquement, lecture seule — l'ensemble minimal qui débloque le dashboard PME côté API :

1. **GET `/me/dashboard/summary`** : agrégat unique consommable par le front pour la page d'accueil. Retourne pour le compte du PME courant :
   - `scores` : derniers scores par référentiel (entité = entreprise) issus de F23 (`score_calculation`).
   - `carbon` : dernière empreinte carbone par année (F28 `carbon_footprint`).
   - `credit_score` : dernier score crédit combiné (F29 `credit_score`).
   - `candidatures` : compteurs par statut + 5 plus récentes (F25 `candidature`).
   - `rapports` : compteurs + 5 plus récents (F24 `rapport_conformite`).
   - `attestations` : compteurs (actives/révoquées) + 5 plus récentes (F30 `attestation`).
   - `next_actions` : 5 prochains `action_step` non clos (F31), tri par `due_at` croissant.

2. **GET `/me/data/export`** (US6 — "Mes données") : export JSON complet et auto-suffisant des données du compte (entreprise, projets, candidatures, scores, attestations, rapports, consentements, action_plan). Aucune donnée hors-compte. RLS strict.

3. **Audit** : chaque appel aux deux endpoints écrit une ligne `audit_log` (action `dashboard_view` ou `data_export`) via le helper `record_audit` existant, scope au compte du PME.

## Hors-scope (DEFERRED)

- US4 carte Leaflet intermédiaires : reporté (frontend Vue + lazy load).
- US7 endpoint historique audit log dédié : couvert par F04 `/me/audit-log` existant. Pas de duplication.
- US8 multi-utilisateurs (invitation, listing, révocation) : reporté (besoin d'un service email + token invitation séparé).
- US9 commentaires sur projets/candidatures : reporté (table + endpoints + composant Vue).
- US2 graphes d'évolution 12 mois : reporté (peut être servi côté front via les endpoints F23/F28/F29 existants).
- Intégralité du frontend Vue (`pages/dashboard/*`, `components/dashboard/*`) : reporté.
- Page `/dashboard/exports` listant les fichiers téléchargeables : reportée (les endpoints sous-jacents F24/F30 existent déjà).

## User Stories couvertes (backend)

| US | Couverture MVP |
|----|---------------|
| US1 — Page d'accueil dashboard | Endpoint `/me/dashboard/summary` agrège scores + candidatures + actions + rapports + attestations en lecture seule. |
| US3 — Statut des candidatures | Inclus dans `summary.candidatures`. |
| US5 — Téléchargements groupés | Compteurs et 5 plus récents dans `summary.rapports` et `summary.attestations`. |
| US6 — Page "Mes données" | Endpoint `/me/data/export` (JSON complet). |
| US10 — Audit qui a fait quoi | Audit log enregistre `dashboard_view` et `data_export` avec `actor_user_id`. |

## Exigences fonctionnelles backend

- **FR-001** : `GET /me/dashboard/summary` accessible uniquement aux PME (`get_current_pme`). 403 si pas d'`account_id`.
- **FR-002** : Réponse JSON conforme au schéma `DashboardSummaryOut`. Latence cible P95 < 500 ms.
- **FR-003** : `GET /me/data/export` retourne un JSON exportable contenant uniquement les données du compte courant.
- **FR-004** : Chaque appel logue une entrée `audit_log` non bloquante (best-effort).
- **FR-005** : Aucune mutation côté DB — endpoints `GET` purs.

## Exigences non-fonctionnelles

- **NFR-001** : RLS strict — un user du compte A ne voit JAMAIS les données du compte B.
- **NFR-002** : Endpoint summary réalisé en N requêtes scope-bornées via SQLAlchemy ; pas de N+1.
- **NFR-003** : Couverture tests ≥ 80 % sur les nouveaux modules.

## Success Criteria

- **SC-001** : `/me/dashboard/summary` répond 200 avec la structure attendue.
- **SC-002** : RLS — deux PME distincts voient strictement leurs propres données.
- **SC-003** : `/me/data/export` produit un JSON valide non vide.
- **SC-004** : Audit log contient une ligne `dashboard_view` après appel.

## Entités

Aucune nouvelle table. Lecture sur : `score_calculation`, `carbon_footprint`, `credit_score`, `candidature`, `rapport_conformite`, `attestation`, `action_step`, plus consommation `record_audit`.

## Risques

- Endpoint summary surchargé : limites strictes (top 5 par catégorie).
- Audit log : best-effort, log warning si insertion échoue.
