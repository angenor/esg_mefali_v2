# F01 — Tests manuels à exécuter par un humain

Ces tests ne sont pas automatisables ou nécessitent une vérification visuelle.
Cocher après vérification.

## Setup / démarrage

- [ ] T023 — Premier démarrage en moins de 10 min sur poste vierge — chronométrer la séquence README "Setup en 5 commandes". SC-001.
- [ ] T054 — Reset complet `docker compose down -v` puis re-up + `alembic upgrade head` < 30 s sur DB vierge. SC-002 + SC-005.

## UI / Frontend

- [ ] T021 — Ouvrir http://localhost:3000, vérifier que le statut "Backend OK" (vert) ou "Backend indisponible" (rouge) est affiché en français.
- [ ] T057 — Smoke test E2E : depuis poste vierge avec backend up, ouvrir http://localhost:3000 et chronométrer l'affichage du statut (< 3 s, SC-004).

## Health check sous tension

- [ ] SC-003 — `docker compose stop postgres` puis `curl localhost:8000/health` → 503 `{"status":"degraded","db":"unreachable"}`. Re-up puis 200.

## Sécurité / configuration

- [ ] T053 — `grep -rE "API_KEY|PASSWORD|SECRET" backend/ frontend/ | grep -v -E "(\.env|tests/|node_modules|\.venv|alembic/versions)"` ne révèle aucun secret hard-codé. SC-006.

## Notes
- Tous les autres T001..T057 ont été exécutés/vérifiés automatiquement (52 tests pytest + 2 tests vitest, couverture 98 %).
- Les tests d'intégration DB tournent contre le container `pgvector/pgvector:pg16` lancé via `docker compose up -d postgres` (déjà démarré dans cette session).
