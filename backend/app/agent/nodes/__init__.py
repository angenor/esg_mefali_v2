"""F53 — Nodes (un fichier par nœud du graph).

Chaque nœud est une fonction asynchrone pure prenant un ``AgentState``
et retournant un patch d'état partiel (dict). Aucun nœud, sauf
``dispatch_tool``, ne MUST écrire en DB ou émettre des effets externes (FR-003).
"""

from __future__ import annotations

__all__: list[str] = []
