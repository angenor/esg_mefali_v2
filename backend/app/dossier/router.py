"""F26 - FastAPI router : POST /me/dossiers/generate (PME, MVP stub)."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_pme
from app.dossier.generator import generate_dossier
from app.dossier.schemas import DossierRequest
from app.models.account_user import AccountUser

router = APIRouter(tags=["dossier"])


def _account_uuid(user: AccountUser) -> UUID:
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "Compte PME non rattache."},
        )
    aid = user.account_id
    return aid if isinstance(aid, UUID) else UUID(str(aid))


@router.post("/me/dossiers/generate", status_code=status.HTTP_200_OK)
def generate_dossier_endpoint(
    body: DossierRequest,
    user: Annotated[AccountUser, Depends(get_current_pme)],
) -> dict[str, Any]:
    """Generate a stub dossier from projet_id + offre_id (FR only).

    MVP: stub data - no DB lookup. Real implementation defers to F19/F21 LLM
    skill (skill_dossier_gcf_via_boad) and persistence in dossier_genere.
    """
    _account_uuid(user)  # auth enforcement only
    projet_stub = {
        "id": str(body.projet_id),
        "titre": "Projet en cours",
        "description": "Description a completer par la PME.",
        "montant": None,
        "devise": None,
    }
    offre_stub = {
        "id": str(body.offre_id),
        "nom": "Offre selectionnee",
        "secteur": None,
        "fonds_nom": None,
    }
    skill_stub: dict[str, Any] = {
        "template": "# Resume executif\n# Contexte\n# Alignement ESG\n# Plan d'action\n",
        "sources": [],
    }
    response = generate_dossier(projet_stub, offre_stub, skill_stub)
    return response.model_dump()
