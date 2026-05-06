# ESG Mefali — Makefile (raccourcis dev)
.PHONY: help setup db-up db-down db-reset migrate backend frontend test test-backend test-frontend lint clean test-guardrails eval-agent eval-jailbreak

help:
	@echo "Cibles disponibles :"
	@echo "  make setup         Installe deps backend (.venv) + frontend (pnpm)"
	@echo "  make db-up         Démarre Postgres dockerisé"
	@echo "  make db-down       Arrête Postgres"
	@echo "  make db-reset      Reset complet (down -v + up + migrate)"
	@echo "  make migrate       Applique les migrations Alembic"
	@echo "  make backend       Démarre uvicorn sur :8010"
	@echo "  make frontend      Démarre Nuxt sur :3001"
	@echo "  make test          Lance backend + frontend tests"
	@echo "  make lint          Lance ruff backend + eslint frontend"

setup:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -r requirements.txt
	cd frontend && pnpm install

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

db-reset:
	docker compose down -v
	docker compose up -d postgres
	@echo "Attente DB ready..."
	@sleep 5
	cd backend && . .venv/bin/activate && alembic upgrade head

migrate:
	cd backend && . .venv/bin/activate && alembic upgrade head

purge-documents:
	cd backend && . .venv/bin/activate && python -m app.scripts.purge_documents

purge-documents-dry-run:
	cd backend && . .venv/bin/activate && python -m app.scripts.purge_documents --dry-run

backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8010

frontend:
	cd frontend && pnpm dev --port 3001

test: test-backend test-frontend

test-backend:
	cd backend && . .venv/bin/activate && pytest --cov

test-frontend:
	cd frontend && pnpm test

lint:
	cd backend && . .venv/bin/activate && ruff check .
	cd frontend && pnpm lint
	bash frontend/scripts/check-no-arbitrary.sh

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	find . -type d -name .ruff_cache -prune -exec rm -rf {} +

# F58 — Agent guardrails & eval
test-guardrails:
	cd backend && . .venv/bin/activate && pytest tests/unit/agent/guardrails/ tests/integration/agent/test_route_anti_injection.py tests/integration/agent/test_select_tools_guardrails.py tests/integration/admin/test_agent_tools_router.py tests/integration/utils/test_ops_alerting.py --cov=app.agent.guardrails --cov-fail-under=85

eval-agent:
	cd backend && . .venv/bin/activate && python scripts/eval_agent.py --mode mock --threshold 0.75 --cases-file tests/golden/agent_e2e.jsonl --report eval_agent_mock_report.json

eval-jailbreak:
	cd backend && . .venv/bin/activate && python scripts/eval_jailbreak.py --mode mock --cases-file tests/golden/jailbreak_prompts.jsonl --report eval_jailbreak_mock_report.json
