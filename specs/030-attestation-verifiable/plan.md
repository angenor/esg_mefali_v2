# Implementation Plan: Attestation Vérifiable (F30)

**Branch**: `030-attestation-verifiable` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/030-attestation-verifiable/spec.md`

## Summary

Livrer le socle MVP de l'attestation vérifiable : la PME génère un PDF signé Ed25519 (canonical
JSON + signature), accessible via QR sur une page publique `/verify/{public_id}` qui affiche
statut/scores/dates et permet de retélécharger le PDF original. La PME et l'admin peuvent révoquer
une attestation. Scope MVP TRÈS focalisé : signature Ed25519, table `attestations`, génération PDF
basique (reportlab + qrcode), endpoints REST, page publique HTML serveur minimaliste, audit log,
RLS. Frontend Nuxt riche, Tools LLM, intégration F26, multi-langue : reportés.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.x / Node 20 (frontend — non touché en MVP)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, `cryptography` (Ed25519),
`reportlab` (PDF), `qrcode[pil]` + Pillow (QR PNG embarqué dans le PDF). Réutilise `app.storage` et
`app.audit.record_audit`.
**Storage**: PostgreSQL 16 + RLS + filesystem local pour PDF via `LocalStorage`
(`attestations/<yyyy>/<mm>/<public_id>.pdf`).
**Testing**: Pytest + pytest-asyncio + httpx. Tests de signature/vérification, génération PDF
(smoke), endpoints (RLS, contrats), expiration, révocation.
**Target Platform**: Linux server FastAPI.
**Project Type**: Web service (backend monorepo).
**Performance Goals**: Génération attestation < 5s P95 ; page `/verify/{public_id}` < 1s ; rate
limit ≥ 60 req/min/IP.
**Constraints**: Plateforme fermée PME + Admin (P7). RLS active (P2). Audit append-only (P3).
Hébergement Europe/Afrique de l'Ouest. Clé privée Ed25519 en variable d'environnement.
**Scale/Scope**: 1 module backend nouveau (`app.attestations`), 1 migration Alembic, ~6 endpoints,
0 page Nuxt en MVP.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: `.specify/memory/constitution.md` v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | La feature ne crée aucune nouvelle entité catalogue. Elle lit les scores existants F23/F29 (déjà sourcés). Le PDF inclut les versions de référentiels (cohérent F04). | OK |
| P2 | Multi-tenant RLS | Nouvelle table `attestations` portera `account_id` + politique RLS standard. Endpoints `/me/...` filtrent par `account_id`. Endpoints publics `/verify/{public_id}` n'exposent que les champs non sensibles. Cross-tenant retourne 404. | OK |
| P3 | Audit log append-only | `attestation.generated`, `attestation.revoked` (PME et admin) inscrits via `record_audit` avec `source_of_change` ∈ {manual, admin}. | OK |
| P4 | Versioning + snapshot | `attestations.scores_inclus_json` stocke un snapshot immuable des scores au moment de la génération, incluant `referentiels_versions_json`. Champ `version` pour soft-revisions. | OK |
| P5 | Money typé | N/A — pas de montants dans l'attestation. | OK |
| P6 | Pivot Indicateur unique | N/A — la feature ne touche pas au pivot indicateurs. | OK |
| P7 | Plateforme fermée | C'est le mécanisme central qui matérialise P7 : pas de rôle externe ; attestation Ed25519 + QR comme seul vecteur de partage. | OK |
| P8 | Édition manuelle + sync LLM | Les attestations ne sont pas alimentées par LLM en MVP (Tools reportés). Champs immuables après émission (sauf `revoked_*`). | OK |
| P9 | Tool-use LLM fiable | N/A — Tools LLM reportés. | OK (reporté) |
| P10 | UX bottom sheet | N/A en MVP — pas de frontend Nuxt riche livré. | OK (reporté) |

**Verdict** : tous les gates passent. Aucune dérogation requise.

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector. MVP backend uniquement.
- Backend `.venv`, Postgres dockerisé.
- Hébergement Europe/Afrique de l'Ouest.
- Langue FR par défaut.
- Clé Ed25519 chargée depuis `ATTESTATION_PRIVATE_KEY` (hex 32 bytes seed) au démarrage ; absence
  ⇒ démarrage OK mais refus de génération avec 503 et message clair côté logs.

## Project Structure

### Documentation (this feature)

```text
specs/030-attestation-verifiable/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── attestation-api.yaml
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── attestations/
│   │   ├── __init__.py
│   │   ├── crypto.py          # load_keys / canonicalize / sign / verify / fingerprint
│   │   ├── pdf_builder.py     # render_attestation_pdf (reportlab + QR)
│   │   ├── service.py         # AttestationService.generate / revoke / list / get_public
│   │   ├── router.py          # /me/attestations + /verify/{public_id} + /admin/attestations
│   │   ├── schemas.py         # Pydantic v2 strict
│   │   └── jobs.py            # expire_attestations (CLI)
│   ├── models/
│   │   └── attestation.py     # SQLAlchemy ORM
│   ├── scripts/
│   │   └── generate_attestation_keys.py
│   └── main.py                # include_router
└── alembic/versions/
    └── 0020_f30_attestations.py

backend/tests/
└── attestations/
    ├── test_crypto.py
    ├── test_service.py
    ├── test_router_me.py
    ├── test_router_admin.py
    ├── test_router_verify.py
    └── test_pdf_builder.py
```

**Structure Decision** : module backend self-contained `app.attestations` aligné sur les modules
existants `app.scoring`, `app.credit`, `app.rapports`. La page `/verify/{public_id}` est un
endpoint FastAPI HTML (template Jinja2 minimal) pour éviter toute dépendance Nuxt en MVP.

## Phase 0 — Research

Voir [research.md](./research.md).

## Phase 1 — Design

- [data-model.md](./data-model.md) : table `attestations`, indices, RLS, contraintes.
- [contracts/attestation-api.yaml](./contracts/attestation-api.yaml) : endpoints REST.
- [quickstart.md](./quickstart.md) : commandes pour générer la paire de clés, lancer les tests,
  vérifier en local.

## Phase 2 — Tasks (/speckit-tasks)

Décomposition livrée dans `tasks.md` au stade `/speckit-tasks`.

## Complexity Tracking

Aucune dérogation constitutionnelle.
