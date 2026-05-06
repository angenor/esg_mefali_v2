"""F54 — Agent context builder (service pur).

Ce package construit le contexte dynamique du system prompt LLM à partir des
données d'une PME (entreprise + projets + candidatures + indicateurs + score
+ plan d'action) et du contexte de page courante.

**Service pur** : aucun module de ce package ne doit importer
``app.chat.api`` ni ``app.agent.runner``. Cette règle est vérifiée par le test
``tests/unit/agent/context/test_no_circular_imports.py`` (NFR-004).

Structure :

- :mod:`app.agent.context.models`         — dataclasses Pydantic immutables.
- :mod:`app.agent.context.escape`         — anti-injection ({{,}} + cap 500).
- :mod:`app.agent.context.tokens`         — count_tokens (tiktoken + fallback).
- :mod:`app.agent.context.money_format`   — affichage monétaire multi-devise.
- :mod:`app.agent.context.cache`          — LRU+TTL hybride (clé account_id).
- :mod:`app.agent.context.loader`         — load_business_context, load_page_context.
- :mod:`app.agent.context.truncation`     — stratégie ordonnée 5 steps.
- :mod:`app.agent.context.sheet_result`   — extraction réponse bottom sheet.
- :mod:`app.agent.context.admin_mode`     — bandeau admin + tools confirmation.
- :mod:`app.agent.context.hashing`        — SHA-256 du prompt construit.
"""
