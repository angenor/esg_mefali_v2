# Implementation Plan: F34 — Extension Guidage / Suivi Candidatures / Notifications / Recommandations

**Branch**: `034-extension-guidage-suivi-notifications` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)

## Summary

Livrer les fondations backend (tables + endpoints + audit + RLS) pour Module 8.4–8.6 :

1. Suivi candidatures PME : `GET /me/candidatures` (liste, slice 200) + `PATCH /me/candidatures/{id}/status`.
2. Centre de notifications PME : nouvelle table `notification` (RLS PME) + `GET /me/notifications` + `PATCH /me/notifications/{id}/read`.
3. Recommandations basiques : `GET /me/extension/offres-recommandees?url=...` qui résout l'URL via `url_pattern` (F33) puis liste les Offres compatibles ; score via service F25 si dispo, sinon `0.0` + tri par fonds source.
4. Service interne `NotificationService.create_for_account(...)` réutilisable par futures features.

Out of scope MVP : panneau latéral UI, mini-chat IA contextuel, création auto de candidature au form, push `chrome.notifications`, cycle `chrome.alarms`, comparateur d'Offres.

## Technical Context

- Language: Python 3.11 (backend uniquement pour ce MVP)
- Backend: FastAPI + SQLAlchemy 2.x + Alembic
- DB: PostgreSQL 16 + RLS (F02), pgvector déjà en place
- Tests: pytest + httpx TestClient (≥80 % couverture sur les modules ajoutés)
- Auth: `get_current_pme` (F02)
- Audit: `record_audit` (F04), actions `notification.read`, `candidature.status_change`
- Réutilisations : `app/extension/url_matcher.py` (F33), `app/matching/*` (F25 si présent)

## Constitution Check

| # | Principe | Application | Status |
|---|----------|-------------|--------|
| P1 | Sourçage anti-hallucination | Endpoints sont pures lectures/mutations utilisateur ; pas de production de claims sourcés. | OK |
| P2 | RLS multi-tenant strict | Table `notification` avec `account_id` + politique RLS PME ; endpoints filtrent par `account_id`. | OK |
| P3 | Audit append-only | `record_audit` invoqué sur chaque mutation (PATCH status, PATCH read). Best-effort wrapper. | OK |
| P4 | Versioning + snapshot | `candidature.version` incrémenté à chaque PATCH ; aucune réécriture de snapshot. | OK |
| P5 | Money typé | N/A. | OK |
| P6 | Pivot Indicateur unique | N/A. | OK |
| P7 | Plateforme fermée | Endpoints PME-only via `get_current_pme`. Pas de nouveau rôle. | OK |
| P8 | Édition manuelle + sync LLM | Notifications créées manuellement par d'autres modules ; pas de génération LLM. | OK |
| P9 | Tool-use LLM fiable | N/A. | OK |
| P10 | UX bottom sheet | N/A (pas de surface UI dans ce MVP). | OK |

Verdict : tous les gates passent.

## Project Structure

```text
backend/app/notifications/
├── __init__.py
├── router.py            # /me/notifications GET, /me/notifications/{id}/read PATCH
├── schemas.py
└── service.py           # NotificationService

backend/app/candidatures/
├── __init__.py
├── router.py            # /me/candidatures GET, /me/candidatures/{id}/status PATCH
├── schemas.py
└── service.py

backend/app/extension/
└── recommendations.py   # GET /me/extension/offres-recommandees (mounté via router existant)

backend/app/models/
└── notification.py      # nouveau modèle SQLAlchemy

backend/alembic/versions/
└── f034_notification_table.py

backend/tests/notifications/
├── __init__.py
├── conftest.py
├── test_notifications_api.py
└── test_notifications_service.py

backend/tests/candidatures/
├── __init__.py
├── conftest.py
└── test_candidatures_api.py

backend/tests/extension/
└── test_offres_recommandees.py
```

## Phase 0 — Research

- Modèle Candidature : déjà en place (`backend/alembic/versions/0001_initial_schema.py` lignes 322-336). Pas de modification de schéma. La progression est lue dans `snapshot_json["progression_pct"]`.
- Audit log : helper `record_audit` (F04) ; pattern wrapper best-effort visible dans `app/extension/router.py`.
- RLS : voir patterns dans migrations existantes pour `chat_message`, `candidature` ; reproduire pour `notification`.
- F25 service de matching : grep `MatchingService` ; s'il n'existe pas dans `app/matching/*`, fallback sur tri par fonds compatible (best-effort, score=0.0).
- `url_matcher` existant (F33 `app/extension/url_matcher.py`) → réutiliser pour résoudre URL→fonds_id/offre_id.
- Auth : `get_current_pme` (F02).

## Phase 1 — Design & Contracts

### Table `notification`

```sql
CREATE TABLE notification (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL REFERENCES account(id),
  user_id UUID NULL REFERENCES account_user(id),
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NULL,
  entity_type TEXT NULL,
  entity_id UUID NULL,
  payload_json JSONB NULL,
  read_at TIMESTAMP NULL,
  version INT NOT NULL DEFAULT 1,
  deleted_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now(),
  CONSTRAINT chk_notification_kind CHECK (kind IN (
    'deadline_j_minus_30','deadline_j_minus_7','deadline_j_minus_1',
    'candidature_inactive','offre_recommandee'
  ))
);
CREATE INDEX ix_notification_account_created ON notification(account_id, created_at DESC);
```

### Endpoints

| Method | Path | Auth | Body | Réponse |
|---|---|---|---|---|
| GET | `/me/candidatures` | PME | – | liste max 200 |
| PATCH | `/me/candidatures/{id}/status` | PME | `{statut}` | `{id, statut, version, updated_at}` |
| GET | `/me/notifications?unread=&limit=&offset=` | PME | – | liste |
| PATCH | `/me/notifications/{id}/read` | PME | – | `{id, read_at}` |
| GET | `/me/extension/offres-recommandees?url=` | PME | – | liste max 10 |

### Validation

- `statut` : Pydantic Literal des 5 valeurs blanches. 422 sinon.
- `kind` : Literal côté service.
- `url` : str non vide ; 422 si manquant.
- `limit` : int 1-200 ; `offset` : int ≥ 0 ; `unread` : bool optionnel.

### Service interne (signatures)

```python
class NotificationService:
    @staticmethod
    def create_for_account(db, *, account_id, kind, title, body=None, user_id=None,
                          entity_type=None, entity_id=None, payload=None) -> Notification: ...
    @staticmethod
    def list_for_account(db, *, account_id, unread=False, limit=50, offset=0) -> list[Notification]: ...
    @staticmethod
    def mark_read(db, *, notification_id, account_id, user_id) -> Notification: ...
```

### Audit actions

- `candidature.status_change` : `entity_type=candidature`, `field=statut`, old/new, `source_of_change=manual`.
- `notification.read` : `entity_type=notification`, `field=read_at`, old=None, new=timestamp.

## Phase 2 — Tasks (à générer par /speckit-tasks)

`tasks.md` produit en aval pour décomposer Phase 1 en tâches actionnables (TDD-first).

## Risks & Mitigations

- Service F25 manquant : fallback best-effort documenté ; tests unitaires valident les deux branches.
- Migration concurrente : F34 ne touche que la nouvelle table `notification`.
- Performance liste candidatures : `LIMIT 200` + index sur `account_id`.
- Volume notifications : index `(account_id, created_at DESC)`.
