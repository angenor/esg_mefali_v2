"""F17 — Tools de mutation LLM (CRUD profil/projet).

Caller : ``app.main`` au démarrage (additif). Tests dans
``backend/tests/orchestrator/tools/mutations/``.
"""

from __future__ import annotations

from app.orchestrator.tools.mutations import (
    create_project,
    delete_project,
    update_company_profile,
    update_project,
)

_REGISTRARS = (
    update_company_profile.register,
    create_project.register,
    update_project.register,
    delete_project.register,
)


def register_mutation_tools() -> None:
    """Enregistre tous les tools de mutation P1 livrés.

    [DEFERRED] : create_candidature, update_candidature_status,
    delete_candidature, attach_document, recompute_score,
    generate_attestation, revoke_attestation, generate_dossier (US3, US6-US10).
    """
    for register in _REGISTRARS:
        register()


__all__ = ["register_mutation_tools"]
