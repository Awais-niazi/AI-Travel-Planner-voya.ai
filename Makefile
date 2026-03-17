.PHONY: help dev stop install test test-go migrate migration lint fmt build-go

help:
	@echo "Voya.ai Backend"
	@echo ""
	@echo "  make dev              Start all services with Docker Compose"
	@echo "  make stop             Stop all services"
	@echo "  make install          Install Python dependencies"
	@echo "  make test             Run Python tests"
	@echo "  make test-go          Run all Go tests"
	@echo "  make migrate          Run Alembic DB migrations"
	@echo "  make migration msg=   Create a new migration"
	@echo "  make lint             Lint Python code"
	@echo "  make fmt              Format Go code"
	@echo "  make build-go         Compile all Go services locally"

dev:
	docker-compose up --build

stop:
	docker-compose down

install:
	.venv/bin/pip install -r requirements.txt

test:
	.venv/bin/pytest tests/ -v --asyncio-mode=auto

lint:
	.venv/bin/ruff check app/ tests/
	.venv/bin/mypy app/

migrate:
	alembic upgrade head

migration:
	alembic revision --autogenerate -m "$(msg)"

test-go:
	@echo "→ Testing recommendation service"
	cd go-services/recommendation && go test ./... -v
	@echo "→ Testing itinerary service"
	cd go-services/itinerary && go test ./... -v
	@echo "→ Testing routing service"
	cd go-services/routing/cmd && go test -v

fmt:
	cd go-services/recommendation && gofmt -w .
	cd go-services/itinerary && gofmt -w .
	cd go-services/routing && gofmt -w .

build-go:
	cd go-services/recommendation && go build ./cmd/main.go
	cd go-services/itinerary && go build ./cmd/main.go
	cd go-services/routing && go build ./cmd/main.go
