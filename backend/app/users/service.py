"""F02 + F42 — Service utilisateurs (me + préférences UX)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.schemas import MeOut
from app.models.account_user import AccountUser
from app.models.user_preferences import UserPreferences
from app.services.audit import record_event
from app.users.schemas import UserPreferencesOut, UserPreferencesPatch


def get_me(user: AccountUser) -> MeOut:
    return MeOut(
        user_id=user.id,
        account_id=user.account_id,
        role=str(user.role),  # type: ignore[arg-type]
        email=user.email,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        email_verified_at=getattr(user, "email_verified_at", None),
    )


# ---------- /me/preferences ----------


def _to_out(prefs: UserPreferences) -> UserPreferencesOut:
    return UserPreferencesOut(
        onboarding_state=prefs.onboarding_state,  # type: ignore[arg-type]
        onboarding_state_updated_at=prefs.onboarding_state_updated_at,
    )


def get_or_create_preferences(db: Session, user: AccountUser) -> UserPreferences:
    """Retourne les préférences de l'utilisateur, les crée par défaut sinon.

    Idempotent : appelé par GET /me/preferences. Tolère une race-condition
    (deux requêtes simultanées) grâce à la contrainte UNIQUE sur user_id.
    """
    prefs = (
        db.query(UserPreferences)
        .filter(UserPreferences.user_id == user.id)
        .first()
    )
    if prefs is not None:
        return prefs

    if user.account_id is None:
        # Sécurité : un admin sans account_id ne peut pas avoir de préférences
        # liées à un tenant — RLS l'exigerait. On lève une exception métier.
        raise ValueError("user_without_account_cannot_have_preferences")

    now = datetime.now(UTC)
    prefs = UserPreferences(
        id=uuid.uuid4(),
        user_id=user.id,
        account_id=user.account_id,
        onboarding_state="pending",
        onboarding_state_updated_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(prefs)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        prefs = (
            db.query(UserPreferences)
            .filter(UserPreferences.user_id == user.id)
            .first()
        )
        assert prefs is not None  # noqa: S101 — race resolved
    return prefs


def update_preferences(
    db: Session, user: AccountUser, patch: UserPreferencesPatch
) -> UserPreferences:
    """Applique une mise à jour partielle. No-op si valeur inchangée."""
    prefs = get_or_create_preferences(db, user)

    if patch.onboarding_state is None:
        return prefs

    new_state = patch.onboarding_state
    old_state = prefs.onboarding_state
    if new_state == old_state:
        return prefs

    now = datetime.now(UTC)
    prefs.onboarding_state = new_state  # type: ignore[assignment]
    prefs.onboarding_state_updated_at = now
    prefs.updated_at = now
    db.flush()

    record_event(
        db,
        event_type="user_preferences.update",
        actor_user_id=user.id,
        actor_account_id=user.account_id,
        entity_type="user_preferences",
        entity_id=prefs.id,
        payload={
            "field": "onboarding_state",
            "old": old_state,
            "new": new_state,
        },
        source_of_change="manual",
    )
    return prefs
