.PHONY: help install dev test lint format clean docker-up docker-down migrate backup restore

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo '$(BLUE)Enterprise SQL Select Project - Makefile Commands$(NC)'
	@echo ''
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# ============================================
# INSTALLATION
# ============================================

install: ## Install all dependencies
	@echo '$(BLUE)Installing Python dependencies...$(NC)'
	cd services/api-python && pip install -r requirements.txt
	@echo '$(GREEN)Dependencies installed!$(NC)'

install-dev: ## Install development dependencies
	@echo '$(BLUE)Installing development dependencies...$(NC)'
	cd services/api-python && pip install -r requirements.txt
	pip install black flake8 mypy isort pytest pytest-cov pre-commit
	pre-commit install
	@echo '$(GREEN)Development environment ready!$(NC)'

# ============================================
# DEVELOPMENT
# ============================================

dev: ## Start development server with hot reload
	@echo '$(BLUE)Starting FastAPI development server...$(NC)'
	cd services/api-python && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-all: ## Start all services with docker-compose
	@echo '$(BLUE)Starting all services...$(NC)'
	docker-compose up -d
	@echo '$(GREEN)All services started!$(NC)'
	@echo 'API Docs: http://localhost:8000/api/v1/docs'
	@echo 'Grafana: http://localhost:3001 (admin/admin)'
	@echo 'Prometheus: http://localhost:9090'
	@echo 'PgAdmin: http://localhost:5050'

logs: ## Show logs from all services
	docker-compose logs -f

# ============================================
# TESTING
# ============================================

test: ## Run all tests
	@echo '$(BLUE)Running tests...$(NC)'
	cd services/api-python && pytest -v

test-cov: ## Run tests with coverage report
	@echo '$(BLUE)Running tests with coverage...$(NC)'
	cd services/api-python && pytest --cov=app --cov-report=html --cov-report=term

test-unit: ## Run unit tests only
	@echo '$(BLUE)Running unit tests...$(NC)'
	cd services/api-python && pytest tests/unit/ -v

test-integration: ## Run integration tests only
	@echo '$(BLUE)Running integration tests...$(NC)'
	cd services/api-python && pytest tests/integration/ -v

test-watch: ## Run tests in watch mode
	@echo '$(BLUE)Running tests in watch mode...$(NC)'
	cd services/api-python && pytest-watch

# ============================================
# CODE QUALITY
# ============================================

lint: ## Run linters
	@echo '$(BLUE)Running linters...$(NC)'
	cd services/api-python && flake8 app/
	cd services/api-python && mypy app/

format: ## Format code with black and isort
	@echo '$(BLUE)Formatting code...$(NC)'
	cd services/api-python && black app/
	cd services/api-python && isort app/
	@echo '$(GREEN)Code formatted!$(NC)'

format-check: ## Check code formatting
	@echo '$(BLUE)Checking code formatting...$(NC)'
	cd services/api-python && black --check app/
	cd services/api-python && isort --check app/

# ============================================
# DOCKER
# ============================================

docker-build: ## Build docker images
	@echo '$(BLUE)Building Docker images...$(NC)'
	docker-compose build
	@echo '$(GREEN)Docker images built!$(NC)'

docker-up: ## Start docker containers
	@echo '$(BLUE)Starting Docker containers...$(NC)'
	docker-compose up -d
	@echo '$(GREEN)Containers started!$(NC)'

docker-down: ## Stop docker containers
	@echo '$(BLUE)Stopping Docker containers...$(NC)'
	docker-compose down
	@echo '$(GREEN)Containers stopped!$(NC)'

docker-restart: ## Restart docker containers
	@echo '$(BLUE)Restarting Docker containers...$(NC)'
	docker-compose restart
	@echo '$(GREEN)Containers restarted!$(NC)'

docker-logs: ## Show docker logs
	docker-compose logs -f

docker-ps: ## List running containers
	docker-compose ps

docker-clean: ## Remove all containers and volumes
	@echo '$(YELLOW)WARNING: This will delete all data!$(NC)'
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		echo '$(GREEN)Cleanup complete!$(NC)'; \
	fi

# ============================================
# DATABASE
# ============================================

db-shell: ## Connect to PostgreSQL shell
	docker-compose exec postgres psql -U postgres -d employees

db-migrate: ## Run database migrations
	@echo '$(BLUE)Running database migrations...$(NC)'
	docker-compose exec postgres psql -U postgres -d employees < database/migrations/V1__create_schema.sql
	docker-compose exec postgres psql -U postgres -d employees < database/migrations/V2__create_functions_and_triggers.sql
	docker-compose exec postgres psql -U postgres -d employees < database/migrations/V3__create_views_and_materialized_views.sql
	docker-compose exec postgres psql -U postgres -d employees < database/migrations/V4__create_indexes_and_optimization.sql
	@echo '$(GREEN)Migrations complete!$(NC)'

db-seed: ## Seed database with initial data
	@echo '$(BLUE)Seeding database...$(NC)'
	docker-compose exec postgres psql -U postgres -d employees < database/scripts/seed_data.sql
	@echo '$(GREEN)Database seeded!$(NC)'

db-reset: ## Reset database (drop and recreate)
	@echo '$(YELLOW)WARNING: This will delete all data!$(NC)'
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS employees;"; \
		docker-compose exec postgres psql -U postgres -c "CREATE DATABASE employees;"; \
		$(MAKE) db-migrate; \
		$(MAKE) db-seed; \
		echo '$(GREEN)Database reset complete!$(NC)'; \
	fi

backup: ## Backup database
	@echo '$(BLUE)Creating database backup...$(NC)'
	./database/scripts/backup.sh
	@echo '$(GREEN)Backup complete!$(NC)'

restore: ## Restore database from backup
	@echo '$(BLUE)Restoring database...$(NC)'
	@read -p "Enter backup file path: " backup_file; \
	./database/scripts/restore.sh $$backup_file

# ============================================
# MONITORING
# ============================================

metrics: ## Open Prometheus metrics
	@open http://localhost:9090 || xdg-open http://localhost:9090

grafana: ## Open Grafana dashboards
	@open http://localhost:3001 || xdg-open http://localhost:3001

logs-elk: ## Open Kibana for logs
	@open http://localhost:5601 || xdg-open http://localhost:5601

traces: ## Open Jaeger for distributed tracing
	@open http://localhost:16686 || xdg-open http://localhost:16686

# ============================================
# DOCUMENTATION
# ============================================

docs: ## Generate API documentation
	@echo '$(BLUE)Opening API documentation...$(NC)'
	@open http://localhost:8000/api/v1/docs || xdg-open http://localhost:8000/api/v1/docs

docs-redoc: ## Open ReDoc documentation
	@open http://localhost:8000/api/v1/redoc || xdg-open http://localhost:8000/api/v1/redoc

# ============================================
# UTILITIES
# ============================================

clean: ## Clean temporary files
	@echo '$(BLUE)Cleaning temporary files...$(NC)'
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	@echo '$(GREEN)Cleanup complete!$(NC)'

check-health: ## Check health of all services
	@echo '$(BLUE)Checking service health...$(NC)'
	@curl -s http://localhost:8000/health | python -m json.tool || echo "FastAPI: DOWN"
	@curl -s http://localhost:9090/-/healthy || echo "Prometheus: DOWN"
	@curl -s http://localhost:3001/api/health || echo "Grafana: DOWN"

status: ## Show status of all services
	@echo '$(BLUE)Service Status:$(NC)'
	@docker-compose ps

version: ## Show version information
	@echo '$(BLUE)Project: Enterprise SQL Select System$(NC)'
	@echo 'Version: 1.0.0'
	@echo 'Python: $(shell python --version)'
	@echo 'Docker: $(shell docker --version)'
	@echo 'Docker Compose: $(shell docker-compose --version)'

# ============================================
# DEPLOYMENT
# ============================================

deploy-dev: ## Deploy to development environment
	@echo '$(BLUE)Deploying to development...$(NC)'
	$(MAKE) docker-build
	$(MAKE) docker-up
	$(MAKE) db-migrate
	@echo '$(GREEN)Deployment complete!$(NC)'

deploy-staging: ## Deploy to staging environment
	@echo '$(BLUE)Deploying to staging...$(NC)'
	@echo '$(YELLOW)Staging deployment not yet configured$(NC)'

deploy-prod: ## Deploy to production environment
	@echo '$(RED)Production deployment requires manual approval$(NC)'
	@echo 'Use CI/CD pipeline for production deployments'

# ============================================
# CI/CD
# ============================================

ci: ## Run CI pipeline locally
	@echo '$(BLUE)Running CI checks...$(NC)'
	$(MAKE) format-check
	$(MAKE) lint
	$(MAKE) test-cov
	@echo '$(GREEN)CI checks passed!$(NC)'

pre-commit: ## Run pre-commit hooks
	pre-commit run --all-files

# ============================================
# DEFAULT
# ============================================

.DEFAULT_GOAL := help
