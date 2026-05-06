"""F56 / T028, T057 — Tests de performance NFR-001 / NFR-008.

NFR-001 : detector < 50 ms p95 sur 2 000 caractères.
NFR-008 : validator < 100 ms p95 par cycle.

Ces tests sont marqués ``@pytest.mark.perf`` ; CI peut les ignorer en mode
rapide via ``pytest -m "not perf"``.
"""

from __future__ import annotations

import statistics
import time

import pytest

from app.agent.sourcing.detector import detect_claims
from app.agent.sourcing.validator import validate_response

_FR_LOREM = (
    "Le facteur ADEME est de 6.0 kg CO2/litre pour le diesel. "
    "Le seuil GCF pour les PME est entre 50 M et 100 M USD selon le pays. "
    "L'AFD prête à un taux de 4,5 % pour des projets entre 5 et 10 ans. "
    "ISO 14064 impose des règles strictes. TCFD recommande la transparence. "
    "Calcul : emissions = consommation * facteur. Le minimum requis est "
    "10 000 EUR. Le BOAD finance les PME ouest-africaines. Production "
    "annuelle de 1200 kWh prévue. La proportion 2/3 est observée. "
    "L'IFC investit jusqu'à 200 millions USD. "
)


def _build_2k_text() -> str:
    text = _FR_LOREM
    while len(text) < 2000:
        text = text + " " + _FR_LOREM
    return text[:2000]


@pytest.mark.perf
def test_detector_p95_under_50ms_for_2kb_text() -> None:
    text = _build_2k_text()
    samples_ms: list[float] = []
    # warmup
    detect_claims(text)
    for _ in range(50):
        t0 = time.perf_counter()
        detect_claims(text)
        samples_ms.append((time.perf_counter() - t0) * 1000)
    p95 = statistics.quantiles(samples_ms, n=20)[18]  # 95th percentile
    assert p95 < 50, f"detector p95={p95:.2f}ms exceeds 50ms (NFR-001)"


@pytest.mark.perf
def test_validator_p95_under_100ms() -> None:
    text = _build_2k_text()
    samples_ms: list[float] = []
    # warmup
    validate_response(text, [], mode="strict")
    for _ in range(50):
        t0 = time.perf_counter()
        validate_response(text, [], mode="strict")
        samples_ms.append((time.perf_counter() - t0) * 1000)
    p95 = statistics.quantiles(samples_ms, n=20)[18]
    assert p95 < 100, f"validator p95={p95:.2f}ms exceeds 100ms (NFR-008)"
