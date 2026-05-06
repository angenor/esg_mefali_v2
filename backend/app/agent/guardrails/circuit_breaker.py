"""F58 — In-memory per-worker circuit breaker (FR-010, FR-011).

State machine: ``closed`` → ``open`` (3 erreurs en 60 s) → ``half_open``
(après 5 min) → ``closed`` (1 succès) ou ``open`` (1 échec).

In-memory uniquement (single uvicorn worker en MVP, cf. clarification Q2).
La coordination multi-worker via Redis est hors-scope MVP.

Aucune dépendance externe (~80 LOC). Lib ``circuitbreaker`` rejetée car non
maintenue depuis 2022.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from time import monotonic
from typing import Final, Literal

logger = logging.getLogger(__name__)

CircuitStateName = Literal["closed", "open", "half_open"]

FALLBACK_MESSAGE: Final[str] = (
    "Le service IA est temporairement indisponible — merci de réessayer "
    "dans quelques minutes."
)


@dataclass
class _CircuitState:
    """État interne d'un service. Mutable (état machine)."""

    name: str
    state: CircuitStateName = "closed"
    error_window: deque[float] = field(default_factory=deque)
    opened_at: float | None = None
    half_open_in_flight: bool = False


class CircuitBreaker:
    """In-memory per-worker circuit breaker pour services externes (LLM)."""

    def __init__(
        self,
        *,
        error_threshold: int = 3,
        time_window_s: int = 60,
        open_duration_s: int = 300,
    ) -> None:
        self._error_threshold = error_threshold
        self._time_window_s = time_window_s
        self._open_duration_s = open_duration_s
        self._states: dict[str, _CircuitState] = {}

    def _state(self, service: str) -> _CircuitState:
        st = self._states.get(service)
        if st is None:
            st = _CircuitState(name=service)
            self._states[service] = st
        return st

    def is_open(self, service: str) -> bool:
        """Retourne True si le circuit est ``open`` (refuse l'appel).

        Bascule automatique en ``half_open`` si la durée d'ouverture est
        expirée ; dans ce cas la fonction renvoie False (autorise une
        tentative de test).
        """
        st = self._state(service)
        now = monotonic()
        if st.state == "open":
            if st.opened_at is not None and (now - st.opened_at) >= self._open_duration_s:
                st.state = "half_open"
                st.half_open_in_flight = True
                logger.info("circuit_breaker[%s] open → half_open", service)
                return False
            return True
        if st.state == "half_open":
            return False
        return False

    def record_success(self, service: str) -> None:
        """Notifie un succès. Ferme le circuit s'il était ``half_open``."""
        st = self._state(service)
        if st.state == "half_open":
            logger.info("circuit_breaker[%s] half_open → closed (success)", service)
            st.state = "closed"
            st.error_window.clear()
            st.opened_at = None
            st.half_open_in_flight = False
            return
        if st.state == "closed":
            # Reset compteur sur succès (évite ouvertures intermittentes)
            st.error_window.clear()

    def record_error(self, service: str, status_code: int | None = None) -> None:
        """Notifie une erreur. Ouvre le circuit si seuil atteint dans la fenêtre."""
        st = self._state(service)
        now = monotonic()
        if st.state == "half_open":
            logger.warning(
                "circuit_breaker[%s] half_open → open (failure status=%s)",
                service,
                status_code,
            )
            st.state = "open"
            st.opened_at = now
            st.half_open_in_flight = False
            return
        # closed → ajoute à la fenêtre roulante
        st.error_window.append(now)
        # Purge des erreurs trop anciennes
        while st.error_window and (now - st.error_window[0]) > self._time_window_s:
            st.error_window.popleft()
        if len(st.error_window) >= self._error_threshold:
            logger.warning(
                "circuit_breaker[%s] closed → open (%d errors in %ds, status=%s)",
                service,
                len(st.error_window),
                self._time_window_s,
                status_code,
            )
            st.state = "open"
            st.opened_at = now

    def reset(self, service: str | None = None) -> None:
        """Réinitialise un service ou tout (réservé aux tests)."""
        if service is None:
            self._states.clear()
        else:
            self._states.pop(service, None)


# Singleton module-level utilisé par ``call_llm`` (FR-010).
LLM_CIRCUIT_BREAKER = CircuitBreaker()


__all__ = [
    "FALLBACK_MESSAGE",
    "LLM_CIRCUIT_BREAKER",
    "CircuitBreaker",
    "CircuitStateName",
]
