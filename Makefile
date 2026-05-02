# ESG Mefali — Makefile (raccourcis dev)
.PHONY: help setup db-up db-down db-reset migrate backend frontend test test-backend test-frontend lint clean

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

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	find . -type d -name .ruff_cache -prune -exec rm -rf {} +
