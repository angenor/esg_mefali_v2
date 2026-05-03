# Phase 1 — Data Model: Onboarding Tour & Auth UX Polish (F42)

**Date**: 2026-05-03
**Branch**: `042-onboarding-auth-polish`
**Migration**: `backend/alembic/versions/0042_user_preferences.py`

---

## 1. Nouvelle table `user_preferences`

Préférences UX évolutives par utilisateur. Relation 1-1 stricte avec `account_user`.

### Schéma

| Colonne | Type | Contrainte | Notes |
|---|---|---|---|
| `id` | `UUID` | `PRIMARY KEY DEFAULT gen_random_uuid()` | |
| `user_id` | `UUID` | `NOT NULL UNIQUE REFERENCES account_user(id) ON DELETE CASCADE` | 1-1 avec user |
| `account_id` | `UUID` | `NOT NULL REFERENCES accounts(id) ON DELETE CASCADE` | RLS |
| `onboarding_state` | `onboarding_state` (enum) | `NOT NULL DEFAULT 'pending'` | `pending` / `completed` / `skipped` / `dismissed` |
| `onboarding_state_updated_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | Mis à jour à chaque transition |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | Trigger ou ORM-side |

### Index

- `UNIQUE (user_id)` (déjà via la contrainte UNIQUE sur la colonne).
- `INDEX idx_user_preferences_account_id ON user_preferences(account_id)` — exigé par la pratique RLS du projet.

### Type enum

```sql
CREATE TYPE onboarding_state AS ENUM ('pending', 'completed', 'skipped', 'dismissed');
```

### RLS

```sql
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_preferences_tenant_isolation ON user_preferences
  USING (account_id = current_setting('app.current_account_id')::uuid);

-- Pas de policy WITH CHECK distincte : la même règle s'applique en INSERT/UPDATE.
```

Un accès à un `user_preferences` d'un autre tenant → 0 row → 404 côté API (jamais 403, P2).

### Audit

Toute mutation (`UPDATE` de `onboarding_state`) DOIT écrire un événement dans `audit_log` :

```json
{
  "user_id": "<actor>",
  "account_id": "<account>",
  "ts": "<iso>",
  "entity": "user_preferences",
  "entity_id": "<row id>",
  "field": "onboarding_state",
  "old": "pending",
  "new": "completed",
  "source_of_change": "manual"
}
```

### Modèle SQLAlchemy

`backend/app/models/user_preferences.py` :

```python
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base

OnboardingState = Literal["pending", "completed", "skipped", "dismissed"]
ONBOARDING_STATES: tuple[OnboardingState, ...] = ("pending", "completed", "skipped", "dismissed")


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("account_user.id", ondelete="CASCADE"), nullable=False, unique=True)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    onboarding_state: Mapped[str] = mapped_column(
        Enum(*ONBOARDING_STATES, name="onboarding_state", native_enum=True),
        nullable=False, default="pending",
    )
    onboarding_state_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

---

## 2. Évolution `account_user` (R5 — invalidation des sessions)

Si la colonne n'existe pas déjà, ajouter dans la même migration `0042` :

| Colonne | Type | Contrainte | Notes |
|---|---|---|---|
| `tokens_invalidated_at` | `TIMESTAMPTZ` | `NULL` (par défaut `NULL`) | Positionnée à `now()` lors d'un reset password réussi. La validation des JWT compare `iat >= tokens_invalidated_at` — toute session antérieure est rejetée. |

**Backfill** : aucun (NULL = pas d'invalidation — comportement courant). À vérifier dans `app/middleware/auth_session.py` que cette colonne est bien lue côté validation.

---

## 3. État du tour — diagramme de transition

```text
                ┌──────────┐
   register OK  │ pending  │   start de welcome.vue
   ───────────► │          │ ─────► driver.js démarre
                └──┬───┬───┘
                   │   │
   bouton          │   │  bouton "Ne plus afficher"
   "Passer" /      │   ▼
   ESC / outside   │ ┌───────────┐
                   │ │ dismissed │ ← terminal sauf restart manuel
                   │ └───────────┘
                   ▼
              ┌─────────┐    dernière étape "Terminer"
              │ skipped │  ────────────────►  ┌───────────┐
              └─────────┘                     │ completed │
                                              └───────────┘
```

**Règles** :
- Toute transition met à jour `onboarding_state_updated_at = now()` et écrit l'audit log.
- L'utilisateur peut appeler `restart()` (point d'entrée manuel — menu Aide) **quel que soit l'état courant**. `restart()` ne change pas l'état : il rouvre simplement driver.js. Si l'utilisateur termine ce restart, l'état devient `completed`. S'il ferme via "Ne plus afficher", `dismissed`.
- Le déclenchement **automatique** au login ne se fait que si `onboarding_state == 'pending'`.

---

## 4. Données transitoires (frontend uniquement)

### 4.1 Brouillon de wizard d'inscription

Stocké en mémoire Pinia store `auth.registerDraft`, **non persisté**. Perdu à la fermeture de l'onglet. Conforme "Hors-scope MVP" sur la sauvegarde inter-session.

### 4.2 Cooldown de renvoi

`localStorage` clé `resend-cooldown:<email>` → timestamp ISO d'expiration. Lue par `ResendCooldownButton.vue`.

### 4.3 Email de "Rester connecté"

Aucune persistance frontend dédiée — la préférence est portée par le cookie de session côté backend (`refresh_token`, TTL 30 jours) qui est positionné si la case est cochée à l'envoi.

---

## 5. Tables consommées en lecture seule (dépendances)

| Source | Table / endpoint | Usage |
|---|---|---|
| F02 | `account_user` | Existence du compte, état `email_verified_at` |
| F02 | `password_reset_tokens` | Validité du token (TTL 60 min, usage unique) |
| F08 | endpoint public `/catalog/secteurs?q=` | Autocomplétion step 2 |
| F11 | endpoint `/me/entreprise/completion` | Décision empty-state vs dashboard |
| F05 | textes CGU/RGPD publiés | Affichés au step 3 |

Aucune mutation de ces ressources par cette feature.

---

## 6. Migration Alembic — résumé

```python
# 0042_user_preferences.py — pseudo-code
def upgrade():
    op.execute("CREATE TYPE onboarding_state AS ENUM ('pending','completed','skipped','dismissed')")
    op.create_table(
        "user_preferences",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("account_user.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("account_id", pg.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("onboarding_state", pg.ENUM(name="onboarding_state", create_type=False), nullable=False, server_default="pending"),
        sa.Column("onboarding_state_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_user_preferences_account_id", "user_preferences", ["account_id"])

    # RLS
    op.execute("ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY user_preferences_tenant_isolation ON user_preferences
        USING (account_id = current_setting('app.current_account_id')::uuid)
    """)

    # Colonne d'invalidation de session si absente
    # (vérifier d'abord avec inspector ; idempotent)
    op.add_column("account_user", sa.Column("tokens_invalidated_at", sa.DateTime(timezone=True), nullable=True))

def downgrade():
    op.drop_column("account_user", "tokens_invalidated_at")
    op.drop_index("idx_user_preferences_account_id", table_name="user_preferences")
    op.drop_table("user_preferences")
    op.execute("DROP TYPE onboarding_state")
```

> NOTE : Vérifier en début d'implémentation si `tokens_invalidated_at` existe déjà sur `account_user` (F02 a peut-être déjà introduit un champ équivalent — `session_version` int). Si oui, **réutiliser** ; ne pas dupliquer.
