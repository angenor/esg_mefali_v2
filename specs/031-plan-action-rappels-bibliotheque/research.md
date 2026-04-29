# Phase 0 Research — F31 Plan d'Action MVP

**Feature**: 031-plan-action-rappels-bibliotheque
**Date**: 2026-04-29

## R-001 — Algo de génération à partir des lacunes F23

**Decision** : extraire les lacunes (indicateurs sous seuil ou manquants) depuis `ScoreCalculation.details_json` du calcul le plus récent du compte, puis pour chaque lacune produire exactement une `ActionStep` avec :
- `title` = `"Combler l'indicateur {code} ({label})"` en FR (template),
- `description` = court paragraphe expliquant l'écart (score actuel vs cible),
- `category` = mapping fixe par pilier ESG → `esg|carbone|credit|candidature` (carbone si pillier `environnement` + indicateur d'émission, sinon `esg`),
- `priority` = mapping severity → `haute|moyenne|basse` :
  - score < 0.30 → `haute`,
  - 0.30 ≤ score < 0.60 → `moyenne`,
  - 0.60 ≤ score < 0.80 → `basse`,
- `horizon_at` = `generated_at + horizon_months / 3` pour `haute`, `+ horizon_months / 2` pour `moyenne`, `+ horizon_months` pour `basse`,
- `status` = `todo`,
- `indicateur_id` = id de l'indicateur source.

**Rationale** : déterministe, testable, traçable, ne réinvente rien. Réutilise les sorties F23 déjà sourcées.

**Alternatives** :
- Génération via LLM → écartée pour MVP (US8 reportée).
- Catalogue figé d'étapes → écarté car non personnalisé.

## R-002 — Étape par défaut si aucune lacune

**Decision** : si `details_json.gaps == []`, créer une étape unique :
- title = "Revue annuelle ESG",
- category = `esg`, priority = `moyenne`,
- horizon_at = `generated_at + horizon_months mois`.

**Rationale** : empêche un plan vide ; donne un point d'entrée même pour une PME en bonne posture.

## R-003 — Concurrence sur le `version`

**Decision** : dans `ActionPlanService.generate`, ouvrir une transaction et exécuter `SELECT MAX(version) FROM action_plan WHERE account_id = :acc FOR UPDATE` avant insert. Cela sérialise les générations concurrentes sur le même account.

**Rationale** : pas de queue, pas de Redis. Postgres `FOR UPDATE` suffit pour 10k comptes.

**Alternatives** :
- Contrainte unique `(account_id, version)` + retry → plus complexe pour le MVP.

## R-004 — RLS sur `action_plan` + `action_step`

**Decision** : politique standard F02 :
```sql
ALTER TABLE action_plan ENABLE ROW LEVEL SECURITY;
CREATE POLICY action_plan_isolation ON action_plan
  USING (account_id = current_setting('app.current_account_id', true)::uuid);

ALTER TABLE action_step ENABLE ROW LEVEL SECURITY;
CREATE POLICY action_step_isolation ON action_step
  USING (
    plan_id IN (SELECT id FROM action_plan
                WHERE account_id = current_setting('app.current_account_id', true)::uuid)
  );
```
Le middleware existant (F02) injecte `SET LOCAL app.current_account_id` à chaque requête HTTP authentifiée. Les accès cross-tenant retournent automatiquement 0 ligne → routes traduisent en 404.

**Rationale** : pattern déjà éprouvé dans F11/F12/F22/F23.

## R-005 — Audit append-only

**Decision** : appeler `app.audit.record_audit(...)` dans :
- `ActionPlanService.generate` après commit du plan (action `create`, before=null, after=plan_dict).
- `ActionPlanService.update_step` (action `update`, before=step_dict avant, after=après).

`source_of_change='manual'` (origine PME), `actor_user_id` du token JWT.

**Rationale** : F04 expose un helper unique, déjà utilisé partout.

## R-006 — Lecture de `ScoreCalculation` la plus récente

**Decision** : `SELECT * FROM score_calculation WHERE account_id = :acc ORDER BY computed_at DESC LIMIT 1`. Si zéro ligne → lever une exception applicative `NoScoreCalculationError` → route renvoie 422 `{"detail":"Aucun score ESG disponible. Lancez un scoring d'abord."}`.

**Rationale** : explicite, simple, conforme aux scénarios d'acceptation.

## R-007 — Format des champs `details_json` consommés

**Decision (assumption documented)** : le service F31 lit `details_json["gaps"]` comme une liste optionnelle d'objets `{indicator_id, indicator_code, indicator_label, score_normalized, pillar}`. Si la structure réelle de F23 diffère, un adaptateur `gap_extractor.py` est isolé pour la résilience. Un map-resolver est implémenté dans `generator.py` (`_extract_gaps(details: dict) -> list[Gap]`).

**Rationale** : isole la dépendance. Les tests unitaires utilisent un payload synthétique.

## R-008 — Tests

**Decision** :
- Unit : algo (mapping severity → priority/horizon), fonction d'extraction des lacunes, service versioning.
- Integration : 3 endpoints + RLS isolation (deux comptes distincts via deux JWT).
- Contract : OpenAPI fragment + test que `app.openapi()` contient bien les 3 routes attendues.

**Rationale** : ≥ 80 % de couverture sur le module `app/action_plan/`.

## R-009 — Hors-scope MVP confirmés

- `notification`, `email_sender`, cron APScheduler → **DEFERRED**.
- Table `ressource`, fiches intermédiaires → **DEFERRED**.
- Frontend Vue, tool LLM `generate_action_plan` → **DEFERRED**.
- Money pour coûts/bénéfices d'étapes → **DEFERRED**.
