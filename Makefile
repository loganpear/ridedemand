.PHONY: backend-up backend-down backend-logs backend-test \
	frontend-install frontend-dev frontend-build frontend-test \
	start stop test-backend test-frontend test-all

## --- Backend (Docker + Python) ---

backend-up:
	docker compose up -d

backend-down:
	docker compose down

backend-logs:
	docker compose logs -f

backend-test:
	pytest -q

test-backend: backend-test

## --- Frontend (React + TypeScript) ---

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

frontend-test:
	cd frontend && npm test

test-frontend: frontend-test

## --- Convenience targets ---

start: backend-up frontend-install
	cd frontend && npm run dev

stop: backend-down

test-all: test-backend test-frontend


