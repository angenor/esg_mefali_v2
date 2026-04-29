# Phase 0 Research — F08 Catalogue Fonds, Intermédiaires & Offres

Toutes les questions [NEEDS CLARIFICATION] de la phase clarify ont été résolues en mode autonome (voir `.cc-runtime/logs/clarify-08.log`). Ce document trace les décisions techniques restantes et les justifications.

## R1 — Schéma JSONB typé pour les critères

**Decision** : Modèle Pydantic v2 strict
```python
class Critere(BaseModel):
    model_config = ConfigDict(extra='forbid')
    key: str                      # ex. "min_project_size"
    operator: Literal['eq','min','max','in','not_in','contains']
    value: Any                    # contraint via @validator selon operator
    unit: str | None = None       # "USD", "MW", "tCO2e/an"...
    source_id: UUID               # FR-011 — sourcing obligatoire par critère
```
Les champs `criteres_json` (Fonds, Intermediaire) sont des `List[Critere]` sérialisés en JSONB.

**Rationale** :
- Déterminisme du calcul `/effective` (clé = `key`, règle = `operator`).
- Traçabilité source par critère (P1 constitution).
- Validation Pydantic v2 stricte (`extra='forbid'`) bloque les champs hallucinés.

**Alternatives rejetées** :
- Free-form JSONB : non testable, perd la traçabilité source.
- Table relationnelle `critere(id, owner_type, owner_id, key, ...)` : over-engineering MVP, complexifie audit & versioning.

## R2 — Algorithme intersection critères

**Decision** : Règles typées par `operator`.

| operator | Sémantique intersection (Fonds vs Intermédiaire) |
|----------|--------------------------------------------------|
| `min` (seuil minimal) | `max(value_fonds, value_inter)` (règle la plus restrictive) |
| `max` (seuil maximal) | `min(value_fonds, value_inter)` |
| `in` (liste éligibilité, ex. `pays`) | `set(value_fonds) ∩ set(value_inter)` ; vide ⇒ `effective_warning` |
| `not_in` (liste exclusion) | `set(value_fonds) ∪ set(value_inter)` |
| `eq` (égalité requise) | `value_fonds` si `value_fonds == value_inter` sinon conflict ⇒ `effective_warning` |
| `contains` (sous-set, ex. `instruments`) | `set(value_fonds) ∩ set(value_inter)` |

**Documents** : toujours UNION par `document_id` (la liste des pièces requises s'additionne).
**Frais Money** : somme `Money` (devises identiques contraintes ou conversion peg si FCFA↔EUR).
**Délais (jours int)** : somme.
**Référentiel** : arbre 2 niveaux `{fonds_layer, intermediaire_layer}` — pas de fusion plate.
**Deadline** : héritage de `fonds.deadline` si Offre n'override pas, sinon `offre.deadline`.

**Rationale** :
- Testable sur 5 cas d'école (SC-002).
- Algorithme purement fonctionnel (pas de state) ⇒ unit testable à 100 %.
- Rejet d'`effective_warning` informatif sans bloquer la création d'Offre (cas conflit, à diagnostiquer manuellement).

**Alternatives rejetées** :
- "Merge dernier gagne" : non-déterministe, viole NFR-001.
- Algorithme custom par critère : ingérable et non-testable.

## R3 — Hook `needs_refresh` synchrone vs async

**Decision** : Synchrone applicatif, dans la transaction de save Fonds/Intermédiaire (PUT/PATCH/publish), avant commit.

**Workflow** :
1. À la mutation publish d'un Fonds (ou Intermédiaire), `needs_refresh_hook` :
   - charge les Offres dérivées via le couple `(fonds_id, intermediaire_id)` (ou `(intermediaire_id, fonds_id)` réciproque).
   - recalcule `criteres_effectifs` + `documents_effectifs` (snapshot N+1).
   - compare au snapshot N stocké côté Offre dans une colonne `effective_snapshot_hash` (sha256).
   - si diff, set `needs_refresh = TRUE` et émet `audit_log` avec diff.
2. Le commit englobe Fonds + Offres flagged → cohérence transactionnelle.

**Rationale** :
- Pas de broker (Celery/RQ) au MVP (stack F01 sans queue).
- Latence acceptable (≤ 50 Offres dérivées par bailleur typique).
- Pas de risque de retard ou de panne worker.

**Alternatives rejetées** :
- Job async (Celery) : nécessite Redis broker, hors stack MVP.
- Cron quotidien : trop tardif pour l'admin qui veut feedback immédiat.

## R4 — Détection automatique `outdated`

**Decision** : Lazy check à la lecture + endpoint admin manuel `POST /admin/offres/recheck-status`.

**Workflow** :
1. À chaque `GET /admin/offres/{id}`, `GET /admin/offres`, `GET /catalog/offres` :
   - service `outdated_lazy_check.py` interroge `accreditation` pour le couple `(fonds_id, intermediaire_id)` ;
   - si `count(WHERE valid_from <= now AND (valid_to IS NULL OR valid_to >= now)) == 0`, transition `published → outdated` (transactionnelle, audit_log).
2. Endpoint admin `POST /admin/offres/recheck-status` parcourt toutes les Offres `published` et applique le check (bulk refresh, idempotent).

**Rationale** :
- Pas de scheduler infra MVP.
- Coût lecture acceptable (1 query indexée par GET).
- Endpoint manuel donne un bouton "tout vérifier" à l'admin pour les exports.

**Alternatives rejetées** :
- Cron : nécessite scheduler (cron OS, APScheduler) hors stack MVP.
- Trigger Postgres : complexifie le schéma, n'audite pas via la couche app.

## R5 — Surface lecture PME du catalogue

**Decision** : Préfixe d'API séparé `/catalog/*` :
- `GET /catalog/fonds` paginé.
- `GET /catalog/fonds/{id}`.
- `GET /catalog/intermediaires` paginé.
- `GET /catalog/intermediaires/{id}`.
- `GET /catalog/offres` paginé (filtres `fonds, intermediaire, pays, secteur, q`).
- `GET /catalog/offres/{id}` (inclut `effective` calculé).

Auth : rôle `pme` requis (plateforme fermée). Réponse exclut `draft`, `archived`, `outdated`.

**Rationale** :
- Sépare clairement le contrat public (PME) du contrat admin.
- RLS plus simple (politique `SELECT` discriminée par `status`).
- Préparation F25 (Matching) qui consommera `/catalog/offres`.

**Alternatives rejetées** :
- Réutiliser `/admin/offres` : confond admin et PME, complique l'autorisation.
- Pas d'endpoint PME au MVP : bloque F25.

## R6 — Money multi-devises

**Decision** :
- Peg FCFA↔EUR fixe à 655.957 (Source `verified` BCEAO, déjà ratifiée par constitution P5).
- USD, GBP, autres : stockés tel quel `(amount, currency)` ; pas de conversion automatique au MVP. La conversion d'affichage est déférée à F32 (dashboard PME).
- Validation : `currency` ∈ {`XOF`, `EUR`, `USD`, `GBP`} (whitelist MVP, extensible).
- `frais_effectifs` = somme stricte si même devise ; warning `mixed_currency_fees` si mélange.

**Rationale** :
- Constitution P5 NON NÉGOCIABLE — `Decimal` partout, peg FCFA-EUR fixe.
- USD reste la devise de la plupart des bailleurs multilatéraux (GCF, IFC), donc présent en MVP.

**Alternatives rejetées** :
- API forex temps réel au MVP : hors scope, dépendance externe.
- Convertir tout en XOF : perd la lisibilité (un GCF affiché en XOF est illisible métier).

## R7 — Indexation Postgres

**Decision** :
- `fonds_source` : btree(`status`, `type`), GIN(`thematique`, `instruments`, `eligibilite_geo`), trigram GIN sur `name`/`organisation` (recherche F06).
- `intermediaire` : btree(`status`, `type`), GIN(`pays`), trigram GIN sur `name`.
- `accreditation` : btree(`intermediaire_id`, `fonds_id`, `valid_from`), btree(`fonds_id`, `valid_from`), btree(`valid_to`).
- `offre` : btree(`status`, `fonds_id`, `intermediaire_id`), unique(`fonds_id`, `intermediaire_id`, `name`), btree(`needs_refresh`), btree(`deadline`).

**Rationale** : couvre les filtres FR-009 (`fonds, intermediaire, pays, secteur, status, q`) et SC-007 (10×).

## R8 — Stratégie de tests pour `effective_calculator`

**Decision** : 5 cas d'école nominatifs codés en `tests/unit/test_effective_calculator.py` paramétrés via `pytest.mark.parametrize` :

| Cas | Fonds | Intermédiaire | Comportement attendu |
|-----|-------|---------------|----------------------|
| 1 | GCF (`min_project_size=10M USD`) | BOAD (`min_project_size=2M USD`) | `min_project_size = 10M USD` (max) |
| 2 | GCF (`pays=['CI','SN','BJ']`) | UNDP (`pays=['SN','ML','CI']`) | `pays = ['CI','SN']` (intersection) |
| 3 | FEM (`instruments=['don','prêt concessionnel']`) | PNUD (`instruments=['don']`) | `instruments = ['don']` |
| 4 | SUNREF (`max_amount=5M EUR`) | Ecobank (`max_amount=8M EUR`) | `max_amount = 5M EUR` (min) |
| 5 | FNE-CI (`pays=['CI']`) | banque locale RDC (`pays=['CD']`) | `effective_warning='incompatible_countries'`, `pays=[]` |

Chaque cas vérifie : `criteres_effectifs`, `documents_effectifs` (union), `frais_effectifs` (somme), `delais_effectifs` (somme), `effective_warning`.

## Conclusion

Aucune NEEDS CLARIFICATION restante. Tous les choix techniques sont alignés avec :
- Constitution v1.0.0 (avec dérogation P2 RLS justifiée pour catalogue global, précédent F07).
- Stack F01–F07 (réutilisation maximale de F06 crud_router/etag/registry/publish_gate, F07 source canonical, F04 audit_log, F01 Money).
- Invariants Module 0 (sourcing, audit, versioning, Money, RLS, bottom sheet, plateforme fermée).

Prêt pour Phase 1 (data-model + contrats).
