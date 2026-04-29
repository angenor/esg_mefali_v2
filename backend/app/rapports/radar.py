"""F24 — Rendu radar PNG par pilier (matplotlib Agg backend).

Fonction pure : prend un dict ``{pillar: score 0-100}`` et renvoie les bytes
d'une image PNG embarquable dans le PDF.
"""

from __future__ import annotations

import io
from collections.abc import Mapping

# Force backend non-GUI avant tout import pyplot.
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

# Ordre canonique des piliers ESG.
_PILLARS_CANONICAL = ("E", "S", "G")


def _normalize_score(value: float | int | None) -> float:
    """Clamp 0..100, None -> 0."""
    if value is None:
        return 0.0
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(100.0, v))


def _ordered_axes(
    scores: Mapping[str, float | int | None],
) -> tuple[list[str], list[float]]:
    """Renvoie (labels, valeurs normalisées) — piliers canoniques d'abord, puis
    autres clés triées alphabétiquement."""
    keys_canonical = [p for p in _PILLARS_CANONICAL if p in scores]
    extras = sorted(k for k in scores.keys() if k not in _PILLARS_CANONICAL)
    labels = keys_canonical + extras
    if not labels:
        labels = list(_PILLARS_CANONICAL)
        return labels, [0.0, 0.0, 0.0]
    values = [_normalize_score(scores.get(k)) for k in labels]
    return labels, values


def render_radar_png(
    scores_by_pillar: Mapping[str, float | int | None],
    *,
    title: str = "Score par pilier",
    size_inches: tuple[float, float] = (4.0, 4.0),
    dpi: int = 150,
) -> bytes:
    """Génère un radar chart en PNG.

    Args:
        scores_by_pillar: dict ``{pillar_code: score}`` (0..100, None possible).
        title: titre du chart.
        size_inches: taille (largeur, hauteur).
        dpi: résolution.

    Returns:
        Bytes PNG (commençant par le header ``\\x89PNG\\r\\n\\x1a\\n``).
    """
    labels, values = _ordered_axes(scores_by_pillar)
    while len(labels) < 3:
        labels.append("·")
        values.append(0.0)
    n = len(labels)

    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    closed_values = values + values[:1]
    closed_angles = angles + angles[:1]

    fig = plt.figure(figsize=size_inches, dpi=dpi)
    try:
        ax = fig.add_subplot(111, polar=True)
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_xticks(angles)
        ax.set_xticklabels(labels)
        ax.set_ylim(0, 100)
        ax.set_yticks([25, 50, 75, 100])
        ax.set_yticklabels(["25", "50", "75", "100"], fontsize=7)
        ax.plot(closed_angles, closed_values, linewidth=1.5, color="#1f77b4")
        ax.fill(closed_angles, closed_values, alpha=0.25, color="#1f77b4")
        ax.set_title(title, fontsize=10, pad=12)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        return buf.getvalue()
    finally:
        plt.close(fig)


PNG_HEADER = b"\x89PNG\r\n\x1a\n"


def is_png(data: bytes) -> bool:
    """Helper pour les tests : vérifie le magic header PNG."""
    return data.startswith(PNG_HEADER)
