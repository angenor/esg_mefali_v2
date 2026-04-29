# Contract — `context_builder.build_context`

**Module**: `app/chat/memory/context_builder.py`
**Date**: 2026-04-29

## Signature

```python
def build_context(
    db: Session,
    *,
    account_id: UUID,
    thread_id: UUID,
    token_budget: int | None = None,  # défaut env CONTEXT_TOKEN_BUDGET (2000)
) -> ContextBundle:
    ...
```

## Pré-conditions

- `account_id` est l'identifiant de compte de la session courante (RLS déjà positionnée).
- `thread_id` appartient au compte (sinon `ValueError`).

## Comportement

1. Charger le profil entreprise via le repository F11 (lecture directe, pas de cache).
2. Charger les projets via le repository F12, filtrés sur statut actif.
3. Charger les 15 derniers messages du thread via `repository.list_recent_messages(thread_id, account_id, limit=15)` (nouvelle fonction F18).
4. Compter le total messages du thread (pour `expose_recall_history`).
5. Compacter via `compactors.compact_profile()` et `compactors.compact_projets(max_n=10)`.
6. Estimer la taille en tokens du rendu markdown.
7. Si `estimated_tokens > token_budget`, exécuter `fit_to_budget()` (compaction déterministe R4).
8. Retourner un `ContextBundle` immuable.

## Post-conditions

- `bundle.estimated_tokens <= token_budget`.
- `bundle.recent_messages` ordonné chronologiquement croissant.
- `bundle.expose_recall_history` est `True` ssi `total_messages_in_thread > 15`.
- Aucun champ sensible n'apparaît dans `profile_section` ni `projects_section` (FR-014).

## Exceptions

- `ValueError` si `thread_id` n'existe pas pour le compte.
- N'attrape pas les exceptions DB — propagation au caller.

## Format `to_system_message()` (exemple synthétique)

```text
# Profil entreprise
Raison sociale : Acme SARL
Secteur : Énergie / Biogaz
Pays : Sénégal
Effectif : 24 salariés
CA : 850000.00 XOF
Description : Production de biogaz à partir de déchets agricoles…

# Projets actifs
- [proj-1] Biogaz Thiès — actif — 1500000.00 XOF — Énergie
  Production de 100 m3 par jour…
- [proj-2] Compostage Dakar — en_cours — 200000.00 XOF — Agriculture
  …

# Conversation récente
[user] Comment je calcule mon empreinte carbone ?
[assistant] Pour ton secteur, je recommande la méthodologie GHG Protocol…
```

## Performance attendue

- p95 < 150 ms (SC-005) sur jeu standard (10 projets, 100 messages dans le thread).
- 2 SELECT supplémentaires par tour (acceptable face à ~1 s de latence LLM).

## Tests obligatoires

- `test_build_context_empty_profile` : profil vide → `profile_section is None`.
- `test_build_context_no_active_projects` : aucun projet actif → `projects_section is None`.
- `test_build_context_window_15` : 20 messages → `len(recent_messages) == 15`, ordre chronologique.
- `test_build_context_budget_compaction` : 25 projets avec descriptions de 2000 chars → `estimated_tokens <= budget`, descriptions tronquées.
- `test_build_context_expose_recall_flag` : 16 messages → `expose_recall_history is True` ; 15 messages → `False`.
- `test_build_context_no_sensitive_fields` : champs sensibles dans la fixture profil → absents du `profile_section`.
- `test_build_context_freshness` : édition profil entre deux appels → 2ᵉ appel reflète la nouvelle valeur (US6).
