# F01 — Tests manuels à exécuter par un humain

Ces tests ne sont pas automatisables ou nécessitent une vérification visuelle.
Cocher après vérification.

## Setup / démarrage

- [ ] T023 — Premier démarrage en moins de 10 min sur poste vierge — chronométrer la séquence README "Setup en 5 commandes". SC-001.
- [ ] T054 — Reset complet `docker compose down -v` puis re-up + `alembic upgrade head` < 30 s sur DB vierge. SC-002 + SC-005.

## UI / Frontend

- [x] T021 — http://localhost:3001 → "Backend OK" affiché en français quand backend up ; bascule en "Backend indisponible" quand `docker compose stop postgres`. ✅ 2026-04-30 agent-browser.
- [ ] T057 — Smoke test E2E chronométré (< 3 s) — non chronométré explicitement, mais affichage observé sous 2 s lors du test T021.

## Health check sous tension

- [x] SC-003 — `docker compose stop postgres` → `curl localhost:8010/health` retourne 503 `{"status":"degraded","db":"unreachable"}` ; après `docker compose up -d postgres` retour à 200 `{"status":"ok","db":"ok"}`. ✅ 2026-04-30.

## Sécurité / configuration

- [ ] T053 — `grep -rE "API_KEY|PASSWORD|SECRET" backend/ frontend/ | grep -v -E "(\.env|tests/|node_modules|\.venv|alembic/versions)"` ne révèle aucun secret hard-codé. SC-006.

## Notes
- Tous les autres T001..T057 ont été exécutés/vérifiés automatiquement (52 tests pytest + 2 tests vitest, couverture 98 %).
- Les tests d'intégration DB tournent contre le container `pgvector/pgvector:pg16` lancé via `docker compose up -d postgres` (déjà démarré dans cette session).
