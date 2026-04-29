# F21 — Manual tests log

## Environnement
- Branche : `021-skills-seed-mvp`
- Date : 2026-04-29
- DB locale : `esg_mefali` (Postgres conteneur `esg_mefali_postgres`)
- Pre-req : `alembic upgrade head` doit avoir applique 0001..0014.

## Etat de la DB locale au moment du run

DB en etat broken au start (alembic_version pointait sur revision phantom
`018_interactive`, table `skill` absente, `account_user` absent). Issue
pre-existante non liee a F21 — `tests/unit/test_migration_smoke.py`
echoue aussi avant F21 (`git stash` + run = meme 6 echecs).

Workaround F21 : tests d'integration F21 marquent `skipif` sur l'absence
de la table `skill` (`requires_skill_schema`). Une fois la DB recreee
proprement, les 6 tests d'integration tournent.

## Tests automatises

### Unit tests (43 tests, 0.17 s)
```bash
cd backend
python -m pytest tests/unit/skills/test_seed_helpers.py \
  tests/unit/skills/test_seed_skills_unit.py --override-ini="addopts=" -q
```
Resultat : `43 passed in 0.17s`.

### Integration (6 tests, skip si DB broken)
```bash
python -m pytest tests/integration/test_seed_skills_e2e.py -q
```
Resultat : `6 skipped` tant que migration F19 non appliquee.

### Coverage
```bash
cat > /tmp/.coveragerc-f21 <<'EOF'
[run]
include =
    app/skills/seed_helpers.py
    scripts/seed_skills.py
[report]
fail_under = 80
show_missing = true
EOF
python -m coverage run --rcfile=/tmp/.coveragerc-f21 -m pytest \
  tests/unit/skills/test_seed_helpers.py \
  tests/unit/skills/test_seed_skills_unit.py \
  --override-ini="addopts=" -q
python -m coverage report --rcfile=/tmp/.coveragerc-f21
```
Resultat :

| Module | Stmts | Miss | Cover |
|--------|-------|------|-------|
| `app/skills/seed_helpers.py` | 119 | 8 | 93% |
| `scripts/seed_skills.py` | 167 | 41 | 75% |
| **TOTAL** | 286 | 49 | **83%** |

Cible >= 80 % : OK.

### Lint
```bash
ruff check app/skills/seed_helpers.py scripts/seed_skills.py \
  tests/unit/skills/test_seed_helpers.py \
  tests/unit/skills/test_seed_skills_unit.py \
  tests/integration/test_seed_skills_e2e.py
```
Resultat : `All checks passed!`.

## Manual smoke (a executer apres `alembic upgrade head` reussi)

1. Lancer le seed sur DB clean :
   ```bash
   cd backend && python -m scripts.seed_skills
   ```
   Attendu : 11 skills creees (3 critical + 8 shells), summary JSON
   imprime sur stdout.

2. Re-run :
   ```bash
   python -m scripts.seed_skills
   ```
   Attendu : `{"created":0,"updated":0,"skipped":0,...}` (pas de bump
   de version).

3. SQL inspection :
   ```sql
   SELECT name, status, version, array_length(tool_whitelist,1) AS n_tools,
          jsonb_array_length(golden_examples) AS n_examples
   FROM skill ORDER BY name;
   ```
   Attendu : 3 critiques avec `n_examples=5`, 8 shells avec
   `n_examples=0`. Statut `published` si sources F07 verifiees, sinon
   `draft` + warning loggue.

4. Modifier le `prompt_expert` d'une fixture critique puis re-run →
   `version` bumpe de 1, `updated=1`.

5. Tester `--only` :
   ```bash
   python -m scripts.seed_skills --only skill_esg_diagnostic
   ```
   Attendu : 1 seule skill traitee.

## Notes / TODO operateur

- Avant exec en dev local, executer un `alembic stamp
  0013_f18_chat_message_embedding_index && alembic upgrade head` pour
  normaliser l'etat alembic.
- Les 8 shells sont volontairement minimales (prompt_expert = TODO) — a
  completer par equipe metier post-MVP.
- L'eval LLM live (`/admin/skills/{id}/run-eval`) n'est PAS execute par
  le script — a faire manuellement post-publication (cf. spec SC-005).
