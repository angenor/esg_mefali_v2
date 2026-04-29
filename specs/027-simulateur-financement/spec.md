# Feature Spec: F27 — Simulateur de Financement

**Branch**: `027-simulateur-financement` | **Date**: 2026-04-29 | **Phase**: 6 — Conseiller Financement (Module 3)
**Source brouillon**: [docs_et_brouillons/features/27-simulateur-financement.md](../../docs_et_brouillons/features/27-simulateur-financement.md)
**Dépendances**: F08 (catalog Offres/Fonds/Intermédiaires), F12 (projets), F25 (matching), F09 (facteurs émission), F05 (Money + peg FCFA-EUR)

## 1. Objectif

Permettre à la PME de **simuler le coût total réel** d'un financement via une Offre :
- décomposition transparente : montant éligible + marges intermédiaire + frais de dossier + garanties + intérêts cumulés sur la durée,
- coût total en pourcentage du montant emprunté,
- différenciation par instrument (subvention / prêt / equity / blending),
- conversion FCFA-EUR au peg fixe (655.957),
- comparateur 2-5 offres côte-à-côte.

Tous les chiffres sont **sourcés** (cohérent F03, NFR-002) et toutes les valeurs financières sont **typées Money** (cohérent F05, NFR-003).

## 2. Scope MVP (P1) vs Deferred

### P1 — Livré dans cette feature

- **US1** : `POST /me/simulations` retourne un `SimulationResult` complet pour un couple `(projet_id, offre_id)` avec coût total décomposé.
- **US2** : prise en compte des `instruments` du fonds (subvention → coût direct = 0 ; prêt → intérêts ; equity → flag dilution).
- **US3** : conversion devise emprunt vs devise PME (FCFA) au peg fixe + flag `change_risk` si devise hors {XOF, EUR}.
- **US6** : `POST /me/simulations/comparator` body `{projet_id, offre_ids:[]}` → tableau aligné des `SimulationResult`.
- **NFR-001 / NFR-002 / NFR-003 / NFR-004** : performance < 200ms, sources, Money typé, gestion `null` explicite.

### Deferred (post-MVP, hors scope F27)

- **US4** : projection d'impact environnemental (CO2e, emplois, bénéficiaires) — branchement F09 reporté à F28. [DEFERRED]
- **US5** : timeline visuelle frontend (tool `show_timeline`). [DEFERRED]
- **US7** : tool LLM `simulate_financing` (intégration F14). [DEFERRED]
- **Frontend Nuxt** : page `/profil/.../simulation`. [DEFERRED]
- **ROI vert IRIS+/Verra**, scénario stress change ±10 %, persistance `simulation_saved`. [DEFERRED]

## 3. User Stories couvertes (P1)

### US1 — Simuler une Offre
**En tant que** PME, **je veux** un endpoint qui calcule le coût total réel d'une Offre, **afin de** comprendre l'engagement réel.

**Critère de validation indépendant** : projet 5M EUR + Offre prêt avec 2 % marge + 1 % frais dossier + 30 % garantie + taux 4 % sur 7 ans → endpoint retourne Money typé pour chaque ligne, somme cohérente, sources jointes.

### US2 — Différencier subvention vs prêt vs equity vs blending
**En tant que** PME, **je veux** que la simulation s'adapte aux `instruments` du fonds, **afin de** comparer pommes avec pommes.

**Critère** : Offre subvention → `cout_total = 0`, flag `instrument='subvention'`. Offre prêt → intérêts cumulés calculés. Offre equity → flag `dilution_warning=true`.

### US3 — Risque de change explicite
**En tant que** PME XOF, **je veux** voir l'équivalent FCFA d'une Offre EUR ou USD, **afin de** ne pas être surprise.

**Critère** : Offre EUR → conversion exacte au peg 655.957, `change_risk=false`. Offre USD → `change_risk=true`, conversion au taux courant si dispo, sinon `change_rate_unknown=true`.

### US6 — Comparateur multi-offres
**En tant que** PME, **je veux** comparer 2-5 Offres côte-à-côte sur coût total, instrument, devise, **afin de** choisir.

**Critère** : `POST /me/simulations/comparator` avec 3 `offre_ids` → tableau aligné de 3 `SimulationResult`, tri par coût total croissant.

## 4. Exigences fonctionnelles couvertes

- **FR-001** : `SimulationService.simulate(db, account_id, projet_id, offre_id, hypotheses?) -> SimulationResult`.
- **FR-002** : `SimulationHypotheses` Pydantic v2 immutable (taux d'intérêt par instrument, durée override, méthodologie ROI=basique).
- **FR-003** : endpoints `POST /me/simulations` et `POST /me/simulations/comparator` (RLS-actée, account_id depuis JWT).
- **FR-006** : chaque ligne du résultat porte `source_ids: list[UUID]` (sources héritées du fonds + intermédiaire + offre).
- **FR-008** : pas de persistance — recalcul à la volée.

## 5. NFR

- **NFR-001** : simulation simple < 200 ms (target P95 sur dataset démo).
- **NFR-002** : aucune valeur affichée sans `source_ids` non vide ou flag `unsourced=true` explicite.
- **NFR-003** : Money typé partout (`amount`, `currency`).
- **NFR-004** : si donnée manquante (taux d'intérêt non précisé), `unknown=true` + label `"Donnée non disponible"` plutôt qu'une valeur inventée.

## 6. Entités

- **`SimulationResult`** (Pydantic, pas de table) : `projet_id`, `offre_id`, `instrument`, `montant_eligible: Money`, `frais_dossier: Money | None`, `marge_intermediaire: Money | None`, `garantie_exigee: Money | None`, `interets_cumules: Money | None`, `cout_total: Money`, `cout_total_pct: Decimal`, `duree_mois: int | None`, `taux_interet_pct: Decimal | None`, `devise_emprunt: Currency`, `equivalent_xof: Money | None`, `change_risk: bool`, `dilution_warning: bool`, `unsourced: bool`, `unknown_fields: list[str]`, `source_ids: list[UUID]`, `notes: list[str]`.

- **`SimulationHypotheses`** : `taux_interet_pct: Decimal | None`, `duree_mois: int | None`, `garantie_pct: Decimal | None`.

- **`ComparatorResult`** : `projet_id`, `rows: list[SimulationResult]`.

## 7. Constitution check

| # | Principe | Statut |
|---|----------|--------|
| P1 | Sourçage anti-hallucination | OK chaque ligne porte `source_ids` ou `unsourced=true` |
| P2 | RLS multi-tenant | OK endpoint `/me/...` RLS par `account_id` JWT |
| P3 | Audit append-only | OK aucune mutation persistée |
| P4 | Versioning candidatures | N/A lecture seule |
| P5 | Money typé | OK NFR-003 |
| P6 | Pivot Indicateur | N/A en P1 |
| P7 | Plateforme fermée | OK endpoints PME `/me/...` only |
| P8 | LLM | N/A en P1 |
| P9 | Tool-use | DEFERRED US7 |
| P10 | UX bottom sheet | N/A backend-only |

## 8. Success criteria

- **SC-001** : simulation projet 5M EUR via Offre prêt → coût total réaliste avec sources non vides.
- **SC-002** : comparateur 3 Offres → tableau ordonné par coût total croissant.
- **SC-003** : Offre USD pour PME XOF → `change_risk=true`.
- **SC-005** : méthodologies (intérêts simples, calcul équivalent peg) documentées dans le code.

## 9. Hors-scope confirmé

- IRIS+/Verra ROI vert.
- Monte-Carlo, scénarios stress.
- Persistance simulations.
- Notifications.
- Blending multi-tranches simultanées.
- Frontend Nuxt.
- Tool LLM `simulate_financing`.
