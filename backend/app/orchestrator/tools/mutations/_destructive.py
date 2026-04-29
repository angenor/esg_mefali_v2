"""F17 — Décorateur ``@destructive`` (FR-002, NFR-003, US4).

Une mutation destructive ne s'exécute que si le payload porte ``confirmed=True``.
Sinon le décorateur retourne un résultat structuré
``MutationConfirmationRequired`` que le LLM doit observer pour déclencher
``ask_yes_no`` avant de réessayer avec ``confirmed=True``.

Caller : ``delete_project`` (et P2 ``delete_candidature``, ``revoke_attestation``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from functools import wraps
from typing import Any


@dataclass(frozen=True)
class MutationConfirmationRequired:
    """Payload retourné quand un tool destructif est invoqué sans confirmation."""

    requires_confirmation: bool = True
    tool: str = ""
    message: str = ""
    impact: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["impact"] = list(self.impact)
        return d


def destructive(
    *,
    tool_name: str,
    message: str,
    impact: tuple[str, ...] = (),
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Décorateur factory.

    Le tool décoré DOIT exposer un kwarg ``confirmed: bool`` (default False).
    Si ``confirmed`` n'est pas explicitement ``True``, le décorateur
    court-circuite l'appel et retourne le payload de confirmation.

    Usage::

        @destructive(tool_name="delete_project", message="Confirmer la suppression ?")
        def handler(*, projet_id, confirmed=False, **kwargs): ...
    """

    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            confirmed = kwargs.get("confirmed")
            if confirmed is None:
                payload = kwargs.get("payload")
                confirmed = getattr(payload, "confirmed", None)
            if confirmed is not True:
                return MutationConfirmationRequired(
                    requires_confirmation=True,
                    tool=tool_name,
                    message=message,
                    impact=tuple(impact),
                ).to_dict()
            return fn(*args, **kwargs)

        return wrapper

    return decorate


__all__ = ["MutationConfirmationRequired", "destructive"]
