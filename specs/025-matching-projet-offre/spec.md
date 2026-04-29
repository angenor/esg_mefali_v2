# Feature Spec: F25 — Matching Projet ↔ Offre

**Branch**: `025-matching-projet-offre` | **Date**: 2026-04-29 | **Phase**: 6 — Conseiller Financement (Module 3)
**Source brouillon**: [docs_et_brouillons/features/25-matching-projet-offre.md](../../docs_et_brouillons/features/25-matching-projet-offre.md)
**Dépendances**: F08 (catalog fonds/intermédiaires/offres), F12 (projets), F23 (scoring multi-référentiels), F04 (audit/snapshot)

## 1. Objectif

Livrer le moteur de matching projet ↔ offre, avec :
- score de compatibilité **décomposé fonds + intermédiaire** (score global = `min(fonds, intermediaire)`),
- détail des critères couverts/manquants par couche, sourcé,
- comparateur d'offres pour un même fonds via différents intermédiaires,
- création de candidature à partir d'une recommandation.

Le matching est toujours **Projet ↔ Offre** (couple Fonds × Intermédiaire), jamais Projet ↔ Fonds nu.

## 2. Scope MVP (P1) vs Deferred

### P1 — Livré dans cette feature

- **US1** : liste d'Offres compatibles pour un projet (`GET /me/projets/{id}/matching`).
- **US2** : score décomposé fonds + intermédiaire + global = `min(fonds, intermediaire)`.
- **US3** : détail des critères couverts/manquants par couche + checklist documents + frais effectifs (Money typé) + délais (`GET /me/projets/{id}/matching/{offre_id}`).
- **US4** : comparateur multi-intermédiaires pour un même fonds (`GET /me/fonds/{fonds_id}/intermediaires-comparator?projet_id=`), 2-3 offres par défaut.
- **US7** : action "Candidater à cette Offre" → `POST /me/projets/{id}/candidatures` body `{offre_id}` → snapshot conforme F04.

### Deferred (post-MVP, hors scope F25)

- **US5** : alertes push / cron `notify_new_matching_calls` (cohérent F31). [DEFERRED]
- **US6** : filtres et tri côté client (le backend supporte déjà des query params simples, frontend reporté). [DEFERRED]
- **US8** : tool LLM `find_offers(projet_id, filters)` (cohérent F14, sera ajouté en F25-bis). [DEFERRED]
- **Frontend Nuxt** : pages `/profil/projets/[id]/matching*` (à livrer dans une itération frontend dédiée). [DEFERRED]

## 3. User Stories couvertes (P1)

### US1 — Voir les Offres compatibles avec mon projet
**En tant que** PME, **je veux** voir une liste d'Offres recommandées triées par compatibilité décroissante, **afin de** identifier les pistes de financement.

**Critère de validation indépendant** : projet renseigné → endpoint matching → liste d'au moins 1 Offre avec score (≥3 si jeu démo complet).

### US2 — Score décomposé fonds + intermédiaire
Chaque Offre affiche `(fonds_score, intermediaire_score, score_global = min(fonds, intermediaire))`.

### US3 — Détail des critères couverts/manquants
Détail d'une Offre : critères du fonds (✓/✗ + source officielle), critères de l'intermédiaire (✓/✗ + source), documents requis (union, dédupliqués), frais effectifs Money typé (FCFA-EUR 655.957), délais effectifs.

### US4 — Comparateur multi-intermédiaires
Tableau comparatif des Offres dérivées d'un même fonds via différents intermédiaires : intermédiaire, score compat., délais, frais, count documents requis.

### US7 — Bouton "Candidater"
Création d'une `candidature` (statut=`brouillon`, snapshot complet projet+offre+scores+critères).

## 4. Exigences fonctionnelles (P1)

- **FR-001** : `MatchingService.match(db, account_id, projet_id, max=10) -> list[OfferMatch]` parcourt les Offres `published` avec accréditation active. Retour trié par `min(fonds, intermediaire)` desc puis par fonds_score desc.
- **FR-002** : Calcul d'un score utilise des heuristiques basées sur les colonnes Fonds/Intermédiaire et `criteres_json` :
  - **plafond/plancher money** : projet.montant_recherche dans `[plancher, plafond]` (conversion FCFA↔EUR via 655.957).
  - **types_impact** ⊆ `thematique` du fonds (au moins 1 commun).
  - **géographie** : projet.pays_iso2 ∈ `eligibilite_geo` du fonds, et ∈ `pays` de l'intermédiaire.
  - **instruments** : projet.structure_financement_arr ∩ `instruments` ≠ ∅ (si renseigné).
  - **critères listés dans `criteres_json`** : chacun évalué en blocking/warning ; blocking non couvert ⇒ score=0.
- **FR-003** : Endpoints PME (RLS) :
  - `GET /me/projets/{id}/matching?limit=10`,
  - `GET /me/projets/{id}/matching/{offre_id}`,
  - `GET /me/fonds/{fonds_id}/intermediaires-comparator?projet_id={uuid}&limit=5`,
  - `POST /me/projets/{id}/candidatures` body `{offre_id}` → 201 `{candidature_id, snapshot_hash}`.
- **FR-004** : Sources cliquables (`source_ids`) propagées sur chaque critère retourné.
- **FR-005** : Snapshot candidature (F04) contient : `projet`, `offre`, `fonds`, `intermediaire`, `scores`, `criteres_couverts`, `criteres_manquants`, `documents_requis`, `frais_effectifs`, `delais_effectifs`, hash SHA-256.
- **FR-006** : Audit append-only sur création candidature (`source_of_change='manual'`).

## 5. Exigences non-fonctionnelles

- **NFR-001** : Matching 100 Offres < 1s (P95) sur jeu démo.
- **NFR-002** : RLS PME : ne voit que ses projets et candidatures.
- **NFR-003** : Money toujours typé `(amount, currency)`, conversion FCFA-EUR via taux fixe 655.957 documenté dans `app/utils/money.py`.
- **NFR-004** : Les Offres avec accréditation expirée OU `status != published` sont exclues.
- **NFR-005** : Couverture tests ≥ 80%.

## 6. Entités / structures

- **OfferMatch** (DTO Python `@dataclass(frozen=True)`).
- **CritereMatch** : `{code, label, severity, covered, source_id, reason}`.
- **Candidature** (table existante 0001) : pas d'évolution schéma, on remplit `snapshot_json`.

## 7. Constitution Check

| # | Principle | Réponse |
|---|-----------|---------|
| P1 | Sourçage anti-hallucination | Oui — `source_ids` propagés. |
| P2 | Multi-tenant RLS | Endpoints `/me/*` filtrent par `account_id` du JWT. |
| P3 | Audit log append-only | Création candidature audite via `record_audit`. |
| P4 | Versioning + snapshot | `snapshot_json` figé + hash. |
| P5 | Money typé FCFA-EUR | `app.utils.money` taux 655.957. |
| P6 | Pivot Indicateur unique | N/A. |
| P7 | Plateforme fermée | Endpoints PME-only. |
| P8 | Édition manuelle + sync LLM | N/A. |
| P9 | Tool-use LLM fiable | Tool `find_offers` reporté (US8 deferred). |
| P10 | UX bottom sheet | Frontend deferred. |

**Verdict** : tous les gates passent.

## 8. Success Criteria

- **SC-001** : Service tourne, retourne format valide pour projet renseigné.
- **SC-002** : Détail montre 2 scores distincts.
- **SC-003** : Comparateur GCF via BOAD vs GCF via UNDP retourne plusieurs lignes.
- **SC-004** : POST candidature crée la ligne avec snapshot_json non-null + audit log.
- **SC-005** : Tests verts, couverture ≥ 80% sur `app/matching/`.

## 9. Risques

- Données projet partielles : si champ manquant ⇒ `reason='value_missing'`, pas de crash.
- Critères blocking non couvert ⇒ score = 0.
