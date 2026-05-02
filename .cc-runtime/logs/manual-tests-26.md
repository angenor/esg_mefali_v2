F26 — Manual tests log
========================
Date: 2026-04-29
Branche: 026-generateur-dossiers-candidatures

État: Phase A (specs) terminée + commit f618602.
Phase B (implémentation backend) — NON LIVRÉE dans ce passage.

Motif:
Le hook gateguard-fact-force impose 4 préambules par Write/Edit. Avec ~12 fichiers
à créer (migration alembic, 2 modèles SQLAlchemy, schemas Pydantic, source_extractor,
validators, prefill, llm_writer, repository, service, exporter, checklist_service,
router + tests unit/integration), le coût en contexte excède le budget restant
de cette session.

Livrables produits:
- specs/026-generateur-dossiers-candidatures/spec.md (US1..US10, FR-001..FR-016, SC-001..SC-007, edge cases, assumptions).
- specs/026-generateur-dossiers-candidatures/plan.md (technical context, constitution gates, project structure, phase 0 research, phase 1 design endpoints + RLS + data model).
- specs/026-generateur-dossiers-candidatures/tasks.md (33 tasks T001..T033 + DEFERRED + mapping FR/US).
- specs/026-generateur-dossiers-candidatures/checklists/requirements.md.
- Skeleton de répertoire backend/app/dossier/ et backend/tests/unit/dossier/ (vides).

Aucun test exécuté (aucune implémentation). Pas de migration appliquée.
Aucune régression possible (aucun code modifié).

Prochain passage:
- Reprendre tasks.md à T001 (migration 0018) et exécuter TDD strict.
- Si gateguard reste actif, segmenter le travail en plusieurs sessions (Phase A→D, puis E→H).
