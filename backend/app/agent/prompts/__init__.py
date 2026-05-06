"""F54 — Templates figés pour le system prompt agent ESG Mefali.

Ce package héberge :

- :mod:`app.agent.prompts.identity`   — bloc d'identité ESG Mefali (immutable).
- :mod:`app.agent.prompts.invariants` — bloc des 10 invariants Module 0
  (immutable) + ``PROMPT_VERSION``.

Toute modification du contenu textuel doit s'accompagner d'une revue manuelle
explicite : le test snapshot
``tests/unit/agent/context/test_invariants_snapshot.py`` (SC-008) échoue tant
que ``snapshots/invariants_2026_05.txt`` n'a pas été régénéré.
"""
