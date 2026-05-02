# Manual tests F30 — Attestation Vérifiable

Date : 2026-04-29
Branche : `030-attestation-verifiable`

## Tests automatisés exécutés

```
$ pytest tests/attestations -q --no-cov
........................   [100%]
24 passed
```

Couverture des modules cœur signature/vérification :

| Module | Couverture |
|--------|-----------|
| `app/attestations/__init__.py` | 100 % |
| `app/attestations/crypto.py` | 100 % |
| `app/attestations/pdf_builder.py` | 100 % |
| `app/attestations/service.py` | 77 % (partiel — chemins router/DB reportés) |

Les modules `router.py` et `schemas.py` ne sont pas couverts en MVP : leurs
tests intégrés requièrent un setup TestClient DB+auth complet, reporté
post-MVP. Le scope MVP minimal vert (signature Ed25519, canonicalisation,
génération PDF, statut, service.generate end-to-end) est entièrement testé.

## Non-régression

```
$ pytest tests/scoring tests/credit tests/rapports tests/carbon --no-cov
173 passed in 2.24s
```

Aucune régression sur F23/F24/F28/F29.

## Lint

```
$ ruff check app/attestations app/models/attestation.py app/scripts/generate_attestation_keys.py
All checks passed!
```

## Smoke imports

```
$ python -c "from app.attestations import crypto, pdf_builder, schemas, service, router; print('imports OK')"
imports OK
```

## Vérifications manuelles complémentaires (à effectuer hors CI)

- [ ] `alembic upgrade head` sur une base test → vérifier création de la table
      `attestation` + RLS + indices.
- [ ] `python -m app.scripts.generate_attestation_keys` → générer une paire,
      coller `ATTESTATION_PRIVATE_KEY_HEX` dans `.env`.
- [x] `uvicorn app.main:app --reload` → `curl /verify/_pubkey` retourne la clé. ✅ 2026-04-30 après ajout de `ATTESTATION_PRIVATE_KEY_HEX` dans `.env` + patch `app/config.py` (load_dotenv pour exposer la var à `os.environ`). Pubkey hex `aaccee5b573fac721986bbb6bede75bcf7404875493f5b0fdf1e3252a68ba405`.
- [x] PME authentifiée → `POST /me/attestations` avec body
      `entreprise_name`, `scores_to_include=["solvability"]`, `scores_resolved`,
      `referentiels_versions`. ✅ 2026-04-30 après fix `app/attestations/router.py` (build response BEFORE commit pour éviter SQLAlchemy `ObjectDeletedError` causé par `expire_on_commit` + RLS sans GUC après commit). Retour 201 avec `id`, `public_id`, `signature_ed25519`, `hash_document`.
- [ ] Vérification externe via le script Python documenté dans `quickstart.md`.
- [x] Page HTML `/verify/{public_id}` rendue dans le navigateur. ✅ 2026-04-30 agent-browser. Affiche entreprise, statut, dates, scores, hash, signature Ed25519, fingerprint pubkey, lien PDF. Tested public_id `e3e912a3-01ac-4ec4-97ed-31a0ca67b093`.
- [x] `POST /me/attestations/{id}/revoke` → la page publique repasse en
      `revoked`. ✅ 2026-04-30 agent-browser. Statut bascule `active` → `revoked` avec timestamp `Revoquee le ...`.
- [x] `GET /verify/{public_id}/json` → 200 retournant tous les champs. ✅ 2026-04-30.
- [x] `GET /verify/{public_id}/download` → 200, PDF (5.3KB, version 1.3, 1 page) avec QR code, titre "Attestation ESG Mefali", PME, ID public, dates, scores, versions référentiels, lien verify. ✅ 2026-04-30 (visualisé via screenshot).
- [x] RLS cross-tenant : PME B logguée → `GET /me/attestations` retourne `[]`, download attestation de PME A → 404. ✅ 2026-04-30.
- [x] Rate-limit `/verify/{public_id}` 60/minute respecté : 59× 200 puis 6× 429. ✅ 2026-04-30.

## Périmètre livré (MVP minimal vert)

- Signature Ed25519 (`cryptography`) — couverte 100 %.
- Canonicalisation JSON déterministe — couverte 100 %.
- Table `attestation` + RLS via Alembic 0020.
- Génération PDF basique `reportlab` + QR — couverte 100 %.
- Service `AttestationService.generate / revoke / list / get_public` — 77 %
  (génération end-to-end testée ; chemins révocation/lookup nécessitent DB
  intégration reportée).
- Router FastAPI : `POST/GET /me/attestations`,
  `POST /me/attestations/{id}/revoke`, `GET /me/attestations/{id}/download`,
  `POST /admin/attestations/{id}/revoke`, `GET /verify/{public_id}` (HTML),
  `GET /verify/{public_id}/json`, `GET /verify/{public_id}/download`,
  `GET /verify/_pubkey`.
- Rate-limit `60/minute` via `app.core.rate_limit.check_rate`.
- Audit log via `record_audit` (F04).
- Script CLI `generate_attestation_keys`.

## Reporté post-MVP

- Tests d'intégration FastAPI TestClient avec DB (fixtures PME/admin/RLS).
- Frontend Nuxt riche (`/profil/attestations`, `/verify/[public_id]` polish).
- Tools LLM (`generate_attestation`, `revoke_attestation`).
- Intégration F26 (inclusion dans dossier de candidature).
- Multi-langue.
- Notifications de révocation.
- Rotation automatique des clés.
- Vérification offline.
