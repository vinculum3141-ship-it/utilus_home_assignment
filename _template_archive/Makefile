.PHONY: help install install-dev test lint format type-check clean run-api run-batch docker-up docker-down

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -e .

install-dev: ## Install development dependencies
	pip install -e ".[dev]"

test: ## Run tests
	pytest

test-cov: ## Run tests with coverage
	pytest --cov=app --cov-report=html --cov-report=term

lint: ## Run linter
	ruff check app/ tests/

format: ## Format code
	black app/ tests/

type-check: ## Run type checker
	mypy app/

clean: ## Clean up generated files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-data: ## Clean data directory (SAFE: only removes data/)
	@echo "🗑️  Cleaning data directory..."
	@if [ -d "data" ]; then \
		rm -rf data/bronze data/silver data/gold data/metadata; \
		echo "✅ Data directory cleaned"; \
	else \
		echo "ℹ️  No data directory found"; \
	fi

run-api: ## Run API server
	uvicorn app.main:app --reload

run-batch: ## Run batch processing with sample data
	energy-platform run-batch --generate-sample

health: ## Check system health
	energy-platform health

docker-build: ## Build Docker image
	docker-compose build

docker-up: ## Start Docker services
	docker-compose up -d

docker-down: ## Stop Docker services
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f app

docker-shell: ## Open shell in app container
	docker-compose exec app bash

docker-batch: ## Run batch processing in Docker
	docker-compose exec app energy-platform run-batch --generate-sample

setup: install-dev ## Initial setup
	cp .env.example .env
	@echo "✅ Setup complete! Edit .env file and run 'make run-batch'"

all: format lint type-check test ## Run all checks
