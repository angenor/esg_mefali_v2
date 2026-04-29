# Tasks — F19

## P1 (MVP)

- [x] T001 — Migration alembic 0014_f19_skill (skill + skill_source + enum)
- [x] T002 — Modèle SQLAlchemy `Skill` + `SkillSource`
- [x] T003 — Pydantic `ActivationRules` + matching (page glob, intent, entity)
- [x] T004 — `priority.py` (ordre domaine + tiebreak)
- [x] T005 — `sources.py` resolve_sources (verified only, 200 chars excerpt)
- [x] T006 — `fusion.py` build_prompt (markdown structuré)
- [x] T007 — `loader.py` load_active_skills (DB query + filtres + priorité)
- [x] T008 — `snapshot.py` snapshot_skill_version (interface no-op + log)
- [x] T009 — Endpoint `/internal/skill-loader/test` (FastAPI router)
- [x] T010 — Tests unitaires (activation, priority, fusion, sources)
- [x] T011 — Test loader (gated requires_db) + test endpoint
- [x] T012 — Coverage ≥ 80% sur app/skills/

## P2 (deferred F20+)

- [ ] T013 — Persistence snapshot dans table `thread_skill` → F20
- [ ] T014 — CRUD admin skill → F20
- [ ] T015 — Cache + invalidation → post-MVP
