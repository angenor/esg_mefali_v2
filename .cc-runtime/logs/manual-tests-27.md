# Manual tests F27 - Simulateur de financement

## Couverture automatique

- 44 tests unitaires/integration sans DB (FakeSession + _build_result).
- Coverage = 83.85% sur app/simulation/.
- Pas de regression : F25 matching tests (46) toujours verts.

## Scenarios couverts en automatise

- SC-001 : projet 5M EUR + Offre pret 2% marge + 1% frais + 30% garantie + 4% / 7 ans -> cout_total = 1 550 000 EUR (31% du montant), sources non vides.
- SC-002 : compare 2 offres -> tri par cout_total asc (subvention en 1er).
- SC-003 : Offre USD pour PME XOF -> change_risk=true, equivalent_xof=None, fx_rate dans unknown_fields.
- SC-005 : methodologie interets simples documentee dans calculator.py.

## Scenarios manuels suggeres post-deploy

1. POST /me/simulations avec un projet existant + Offre publishee -> verifier le JSON inclut Money typed sur tous les montants et source_ids non vide.
2. POST /me/simulations/comparator avec 5 offres -> verifier le tri.
3. POST /me/simulations avec offre_id d'une offre draft (non publiee) -> 404 offre_not_found.
4. POST /me/simulations sans JWT -> 401.
5. POST /me/simulations avec projet d'un autre account -> RLS bloque -> 404 projet_not_found.

## Hors scope (DEFERRED)

- US4 impact CO2e -> F28.
- US5 timeline frontend.
- US7 tool LLM `simulate_financing`.
- Page Nuxt frontend.
