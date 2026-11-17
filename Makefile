.PHONY: setup dev api web sync test lint format types types-check check up down logs

setup: ## instala dependências e cria os arquivos .env
	cd backend && uv sync
	cd frontend && npm install
	@test -f backend/.env || cp backend/.env.example backend/.env
	@test -f frontend/.env.local || cp frontend/.env.example frontend/.env.local
	@echo "Pronto. Rode 'make sync' para baixar os dados e depois 'make dev'."

dev: ## sobe API (8000) e telas (3000) juntas
	@trap 'kill 0' INT TERM; \
	(cd backend && uv run uvicorn app.main:app --reload --port 8000) & \
	(cd frontend && npm run dev) & \
	wait

api:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

web:
	cd frontend && npm run dev

sync: ## baixa/atualiza os dados (ex.: make sync ETAPAS=macro,mercado)
	cd backend && uv run python -m app.jobs.sync --etapas "$(ETAPAS)"

test: ## testes com cobertura mínima (back) e testes do front
	cd backend && uv run pytest -q --cov
	cd frontend && npm test

lint: ## ruff, formatação, mypy e regras da casa (back); eslint, tsc e prettier (front)
	cd backend && uv run ruff check app tests tools alembic
	cd backend && uv run ruff format --check app tests tools alembic
	cd backend && uv run mypy app tools
	cd backend && uv run python -m tools.style_rules app tests tools alembic
	cd frontend && npm run lint && npm run typecheck && npm run format:check

format: ## aplica ruff format e prettier
	cd backend && uv run ruff check --fix app tests tools alembic && uv run ruff format app tests tools alembic
	cd frontend && npm run format

types: ## regenera os tipos do front a partir do OpenAPI da API
	cd backend && uv run python -m tools.export_openapi
	cd frontend && npm run gen:types

types-check: types ## falha se openapi.json ou schema.d.ts estavam desatualizados
	git diff --exit-code -- openapi.json frontend/src/lib/api/schema.d.ts

check: lint test ## tudo o que a CI roda

up: ## sobe API (8000) e telas (3000) no Docker; na primeira vez baixa os dados sozinho
	docker compose up -d --build --wait
	@echo "Pronto: http://localhost:3000 (telas) e http://localhost:8000/docs (API)"

down: ## para os containers (os dados ficam no volume)
	docker compose down

logs: ## acompanha os logs da API e do front
	docker compose logs -f
