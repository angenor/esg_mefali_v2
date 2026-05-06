"""F58 / T042 — Tests unitaires CircuitBreaker (FR-010, FR-011, FR-026)."""

from __future__ import annotations

import time

import pytest

from app.agent.guardrails.circuit_breaker import (
    FALLBACK_MESSAGE,
    CircuitBreaker,
)


@pytest.mark.unit
def test_initial_state_closed() -> None:
    cb = CircuitBreaker(error_threshold=3, time_window_s=60, open_duration_s=300)
    assert cb.is_open("svc") is False


@pytest.mark.unit
def test_opens_after_threshold_errors() -> None:
    cb = CircuitBreaker(error_threshold=3, time_window_s=60, open_duration_s=300)
    for _ in range(3):
        cb.record_error("svc", status_code=503)
    assert cb.is_open("svc") is True


@pytest.mark.unit
def test_records_success_resets_error_count_and_closes() -> None:
    cb = CircuitBreaker(error_threshold=3, time_window_s=60, open_duration_s=300)
    cb.record_error("svc")
    cb.record_error("svc")
    cb.record_success("svc")
    # Après un succès, retour en closed (ou maintien — mais le compteur reset)
    cb.record_error("svc")  # 1 erreur seule, ne doit PAS ouvrir
    assert cb.is_open("svc") is False


@pytest.mark.unit
def test_window_expiration_resets_count() -> None:
    cb = CircuitBreaker(error_threshold=3, time_window_s=1, open_duration_s=300)
    cb.record_error("svc")
    cb.record_error("svc")
    time.sleep(1.1)  # fenêtre expire
    cb.record_error("svc")  # ne doit PAS ouvrir (autres sont expirés)
    assert cb.is_open("svc") is False


@pytest.mark.unit
def test_half_open_after_open_duration() -> None:
    cb = CircuitBreaker(error_threshold=2, time_window_s=60, open_duration_s=1)
    cb.record_error("svc")
    cb.record_error("svc")
    assert cb.is_open("svc") is True
    time.sleep(1.1)  # passe en half_open
    # is_open doit retourner False (autorise une tentative)
    assert cb.is_open("svc") is False


@pytest.mark.unit
def test_half_open_success_closes() -> None:
    cb = CircuitBreaker(error_threshold=2, time_window_s=60, open_duration_s=1)
    cb.record_error("svc")
    cb.record_error("svc")
    time.sleep(1.1)
    # is_open() bascule en half_open ; on simule un succès
    _ = cb.is_open("svc")
    cb.record_success("svc")
    assert cb.is_open("svc") is False


@pytest.mark.unit
def test_half_open_failure_re_opens() -> None:
    cb = CircuitBreaker(error_threshold=2, time_window_s=60, open_duration_s=1)
    cb.record_error("svc")
    cb.record_error("svc")
    time.sleep(1.1)
    _ = cb.is_open("svc")  # half_open
    cb.record_error("svc")  # échec en half_open → re-ouvre
    assert cb.is_open("svc") is True


@pytest.mark.unit
def test_isolated_per_service() -> None:
    cb = CircuitBreaker(error_threshold=2, time_window_s=60, open_duration_s=300)
    cb.record_error("svc_a")
    cb.record_error("svc_a")
    assert cb.is_open("svc_a") is True
    assert cb.is_open("svc_b") is False


@pytest.mark.unit
def test_fallback_message_is_french() -> None:
    assert "service" in FALLBACK_MESSAGE.lower()
    assert "indisponible" in FALLBACK_MESSAGE.lower()
