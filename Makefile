# Expense Tracker - Development Commands
# Run 'make help' to see all available commands

.PHONY: help install install-dev test test-unit test-integration lint format security docker-build docker-test clean coverage check-all

# Default Python and pip commands
PYTHON = python
PIP = pip
PYTEST = pytest
DOCKER = docker

# Colors for output
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[0;33m
BLUE = \033[0;34m
NC = \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Expense Tracker - Development Commands$(NC)"
	@echo "======================================"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt -r requirements-test.txt

test: ## Run all tests with coverage
	@echo "$(BLUE)Running all tests with coverage...$(NC)"
	$(PYTEST) tests/ --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml -v

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	$(PYTEST) tests/ -m "not integration" --cov=app --cov-report=term-missing -v

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(PYTEST) tests/ -m "integration" -v

test-fast: ## Run tests without coverage (faster)
	@echo "$(BLUE)Running fast tests...$(NC)"
	$(PYTEST) tests/ -v --tb=short

lint: ## Run all linting checks
	@echo "$(BLUE)Running linting checks...$(NC)"
	@echo "$(YELLOW)Running ruff...$(NC)"
	ruff check app/
	@echo "$(YELLOW)Running flake8...$(NC)"
	flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 app/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	@echo "$(YELLOW)Checking code formatting with black...$(NC)"
	black --check --diff app/
	@echo "$(YELLOW)Checking import order with isort...$(NC)"
	isort --check-only --diff app/

format: ## Format code with black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	black app/
	isort app/
	@echo "$(GREEN)Code formatting complete!$(NC)"

lint-fix: ## Fix linting issues automatically
	@echo "$(BLUE)Fixing linting issues...$(NC)"
	ruff check app/ --fix
	black app/
	isort app/
	@echo "$(GREEN)Auto-fix complete!$(NC)"

security: ## Run security scans
	@echo "$(BLUE)Running security scans...$(NC)"
	@echo "$(YELLOW)Running bandit security scan...$(NC)"
	bandit -r app/ -f json -o bandit-report.json || true
	bandit -r app/ --severity-level medium
	@echo "$(YELLOW)Checking for security vulnerabilities in dependencies...$(NC)"
	safety check --json --output safety-report.json || true
	safety check

docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	$(DOCKER) build -t expense-tracker:latest .

docker-test: docker-build ## Test Docker image
	@echo "$(BLUE)Testing Docker image...$(NC)"
	$(DOCKER) run --rm expense-tracker:latest python -c "import app; print('✅ Docker image working!')"

docker-run: docker-build ## Run application in Docker
	@echo "$(BLUE)Running application in Docker...$(NC)"
	$(DOCKER) run -d --name expense-tracker-test \
		-e MYSQL_HOST=host.docker.internal \
		-e MYSQL_USER=root \
		-e MYSQL_PASSWORD=your_password \
		-e MYSQL_DATABASE=expense_tracker \
		-e SECRET_KEY=test_secret_key \
		-p 8000:8000 \
		expense-tracker:latest
	@echo "$(GREEN)Application running at http://localhost:8000$(NC)"
	@echo "$(YELLOW)Stop with: docker stop expense-tracker-test && docker rm expense-tracker-test$(NC)"

docker-dev: ## Run development environment with Docker Compose
	@echo "$(BLUE)Starting development environment...$(NC)"
	docker-compose up --build

docker-prod: ## Run production environment with Docker Compose
	@echo "$(BLUE)Starting production environment...$(NC)"
	docker-compose -f docker-compose.prod.yml up -d
	@echo "$(GREEN)Production environment started$(NC)"
	@echo "$(YELLOW)Monitor with: docker-compose -f docker-compose.prod.yml logs -f$(NC)"

docker-stop: ## Stop all Docker containers
	@echo "$(BLUE)Stopping Docker containers...$(NC)"
	docker-compose down 2>/dev/null || true
	docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
	docker stop expense-tracker-test 2>/dev/null || true
	docker rm expense-tracker-test 2>/dev/null || true
	@echo "$(GREEN)Docker containers stopped$(NC)"

docker-logs: ## Show Docker container logs
	@echo "$(BLUE)Showing Docker logs...$(NC)"
	docker-compose logs -f

docker-logs-prod: ## Show production Docker container logs
	@echo "$(BLUE)Showing production Docker logs...$(NC)"
	docker-compose -f docker-compose.prod.yml logs -f

docker-shell: ## Access application container shell
	@echo "$(BLUE)Accessing container shell...$(NC)"
	docker exec -it expense-tracker-app bash || docker exec -it expense-tracker-app-prod bash

docker-db-shell: ## Access database container shell
	@echo "$(BLUE)Accessing database shell...$(NC)"
	docker exec -it expense-tracker-mysql mysql -u root -p || docker exec -it expense-tracker-mysql-prod mysql -u root -p

docker-push: docker-build ## Build and push Docker image
	@echo "$(BLUE)Pushing Docker image...$(NC)"
	$(DOCKER) tag expense-tracker:latest $(IMAGE_NAME):latest 2>/dev/null || echo "$(YELLOW)Set IMAGE_NAME environment variable to push to registry$(NC)"
	$(DOCKER) push $(IMAGE_NAME):latest 2>/dev/null || echo "$(YELLOW)Set IMAGE_NAME environment variable to push to registry$(NC)"

docker-pull: ## Pull latest Docker image
	@echo "$(BLUE)Pulling Docker image...$(NC)"
	$(DOCKER) pull $(IMAGE_NAME):latest 2>/dev/null || echo "$(YELLOW)Set IMAGE_NAME environment variable to pull from registry$(NC)"

docker-health: ## Check Docker container health
	@echo "$(BLUE)Checking container health...$(NC)"
	@echo "Development containers:"
	@docker ps --filter "name=expense-tracker" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "No development containers running"
	@echo ""
	@echo "Production containers:"
	@docker ps --filter "name=expense-tracker-.*-prod" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "No production containers running"

docker-backup: ## Backup Docker volumes and data
	@echo "$(BLUE)Creating Docker backup...$(NC)"
	@mkdir -p backups
	@BACKUP_DATE=$$(date +%Y%m%d_%H%M%S) && \
	echo "Creating backup: backups/expense-tracker-backup-$$BACKUP_DATE.tar.gz" && \
	docker run --rm -v expense_tracker_mysql_data:/data -v $(PWD)/backups:/backup alpine \
		tar -czf /backup/mysql-data-$$BACKUP_DATE.tar.gz -C /data . && \
	docker run --rm -v expense_tracker_uploads_data:/data -v $(PWD)/backups:/backup alpine \
		tar -czf /backup/uploads-data-$$BACKUP_DATE.tar.gz -C /data . && \
	echo "$(GREEN)Backup completed: backups/*-$$BACKUP_DATE.tar.gz$(NC)"

docker-restore: ## Restore Docker volumes from backup (specify BACKUP_FILE=filename)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "$(RED)Please specify backup file: make docker-restore BACKUP_FILE=mysql-data-20240101_120000.tar.gz$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Restoring from backup: $(BACKUP_FILE)...$(NC)"
	@echo "$(RED)⚠️  This will overwrite existing data! Press Ctrl+C to cancel...$(NC)"
	@sleep 5
	@if [[ "$(BACKUP_FILE)" == *mysql* ]]; then \
		docker run --rm -v expense_tracker_mysql_data:/data -v $(PWD)/backups:/backup alpine \
			tar -xzf /backup/$(BACKUP_FILE) -C /data; \
	elif [[ "$(BACKUP_FILE)" == *uploads* ]]; then \
		docker run --rm -v expense_tracker_uploads_data:/data -v $(PWD)/backups:/backup alpine \
			tar -xzf /backup/$(BACKUP_FILE) -C /data; \
	else \
		echo "$(RED)Unknown backup type: $(BACKUP_FILE)$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Restore completed$(NC)"

coverage: test ## Generate and open coverage report
	@echo "$(BLUE)Opening coverage report...$(NC)"
	@if command -v open >/dev/null 2>&1; then \
		open htmlcov/index.html; \
	elif command -v xdg-open >/dev/null 2>&1; then \
		xdg-open htmlcov/index.html; \
	elif command -v start >/dev/null 2>&1; then \
		start htmlcov/index.html; \
	else \
		echo "$(YELLOW)Coverage report generated in htmlcov/index.html$(NC)"; \
	fi

clean: ## Clean up generated files
	@echo "$(BLUE)Cleaning up...$(NC)"
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf bandit-report.json
	rm -rf safety-report.json
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	$(DOCKER) system prune -f 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete!$(NC)"

check-all: lint security test ## Run all checks (CI simulation)
	@echo "$(GREEN)✅ All checks passed! Ready for CI/CD$(NC)"

setup-db: ## Set up the database
	@echo "$(BLUE)Setting up database...$(NC)"
	$(PYTHON) setup_database.py

run-dev: ## Run development server
	@echo "$(BLUE)Starting development server...$(NC)"
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## Run production server
	@echo "$(BLUE)Starting production server...$(NC)"
	uvicorn app.main:app --host 0.0.0.0 --port 8000

# Development workflow targets
dev-setup: install-dev setup-db ## Complete development setup
	@echo "$(GREEN)✅ Development environment ready!$(NC)"
	@echo "$(YELLOW)Run 'make run-dev' to start the server$(NC)"

ci-local: clean check-all ## Run full CI pipeline locally
	@echo "$(GREEN)🎉 Local CI pipeline completed successfully!$(NC)"

# Quick development commands
quick-test: ## Quick test run (no coverage)
	$(PYTEST) tests/ --tb=short -q

quick-lint: ## Quick lint check (ruff only)
	ruff check app/

# Database commands
db-reset: ## Reset database (careful!)
	@echo "$(RED)⚠️  This will reset the database! Press Ctrl+C to cancel...$(NC)"
	@sleep 3
	$(PYTHON) setup_database.py --reset

# Dependency management
update-deps: ## Update all dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 $(PIP) install -U
	$(PIP) freeze > requirements.txt.new
	@echo "$(YELLOW)New requirements saved to requirements.txt.new$(NC)"
	@echo "$(YELLOW)Review and replace requirements.txt if needed$(NC)"

# Git hooks setup
setup-hooks: ## Set up git pre-commit hooks
	@echo "$(BLUE)Setting up git hooks...$(NC)"
	echo '#!/bin/bash\nmake quick-lint && make quick-test' > .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "$(GREEN)✅ Git pre-commit hooks installed$(NC)"

# Help for specific environments
help-docker: ## Docker-specific help
	@echo "$(BLUE)Docker Commands:$(NC)"
	@echo "  make docker-build    - Build the Docker image"
	@echo "  make docker-test     - Test the Docker image"
	@echo "  make docker-run      - Run in Docker container"
	@echo ""
	@echo "$(YELLOW)Docker Prerequisites:$(NC)"
	@echo "  - Docker installed and running"
	@echo "  - MySQL container or external MySQL available"

help-ci: ## CI/CD pipeline help
	@echo "$(BLUE)CI/CD Commands:$(NC)"
	@echo "  make ci-local        - Run full CI pipeline locally"
	@echo "  make check-all       - Run all quality checks"
	@echo "  make lint            - Code quality checks"
	@echo "  make security        - Security vulnerability scans"
	@echo "  make test            - Full test suite with coverage"
	@echo ""
	@echo "$(YELLOW)Files:$(NC)"
	@echo "  .github/workflows/ci.yml  - GitHub Actions pipeline"
	@echo "  pyproject.toml           - Tool configuration"
	@echo "  requirements-test.txt    - Test dependencies"

# Kubernetes deployment commands
k8s-deploy: ## Deploy to Kubernetes (default environment)
	@echo "$(BLUE)Deploying to Kubernetes...$(NC)"
	./scripts/k8s-deploy.sh

k8s-deploy-dev: ## Deploy to Kubernetes development environment
	@echo "$(BLUE)Deploying to Kubernetes (development)...$(NC)"
	./scripts/k8s-deploy.sh development

k8s-deploy-prod: ## Deploy to Kubernetes production environment
	@echo "$(BLUE)Deploying to Kubernetes (production)...$(NC)"
	./scripts/k8s-deploy.sh production

k8s-status: ## Check Kubernetes deployment status
	@echo "$(BLUE)Checking Kubernetes status...$(NC)"
	./scripts/k8s-deploy.sh default status

k8s-logs: ## Show Kubernetes logs
	@echo "$(BLUE)Showing Kubernetes logs...$(NC)"
	./scripts/k8s-deploy.sh default logs

k8s-delete: ## Delete Kubernetes deployment
	@echo "$(BLUE)Deleting Kubernetes deployment...$(NC)"
	./scripts/k8s-deploy.sh default delete

k8s-update: ## Update Kubernetes image (specify IMAGE_TAG=version)
	@echo "$(BLUE)Updating Kubernetes image...$(NC)"
	./scripts/k8s-deploy.sh default update $(IMAGE_TAG)

k8s-port-forward: ## Port forward to application service
	@echo "$(BLUE)Setting up port forwarding...$(NC)"
	@echo "Access at http://localhost:8080"
	kubectl port-forward -n expense-tracker service/nginx-service 8080:80

k8s-shell: ## Access application pod shell
	@echo "$(BLUE)Accessing application pod shell...$(NC)"
	kubectl exec -it -n expense-tracker deployment/expense-tracker-app -- /bin/bash

k8s-db-shell: ## Access database pod shell
	@echo "$(BLUE)Accessing database pod shell...$(NC)"
	kubectl exec -it -n expense-tracker deployment/mysql -- mysql -u root -p

k8s-secrets: ## Create/update Kubernetes secrets interactively
	@echo "$(BLUE)Updating Kubernetes secrets...$(NC)"
	@echo "$(YELLOW)Current secrets (base64 decode them to see values):$(NC)"
	@kubectl get secret expense-tracker-secrets -n expense-tracker -o yaml 2>/dev/null || echo "No secrets found"
	@echo ""
	@echo "$(YELLOW)To create/update secrets:$(NC)"
	@echo "1. Edit k8s/secret.yaml with base64 encoded values"
	@echo "2. Run: kubectl apply -f k8s/secret.yaml"
	@echo ""
	@echo "$(YELLOW)To encode a value:$(NC)"
	@echo "echo -n 'your_secret_value' | base64"

help-k8s: ## Kubernetes deployment help
	@echo "$(BLUE)Kubernetes Commands:$(NC)"
	@echo "  make k8s-deploy      - Deploy to Kubernetes (default)"
	@echo "  make k8s-deploy-dev  - Deploy development environment"
	@echo "  make k8s-deploy-prod - Deploy production environment"
	@echo "  make k8s-status      - Check deployment status"
	@echo "  make k8s-logs        - Show application logs"
	@echo "  make k8s-delete      - Delete deployment"
	@echo "  make k8s-update      - Update image (set IMAGE_TAG=version)"
	@echo "  make k8s-port-forward - Port forward to access locally"
	@echo "  make k8s-shell       - Access application pod"
	@echo "  make k8s-db-shell    - Access database pod"
	@echo "  make k8s-secrets     - Manage secrets"
	@echo ""
	@echo "$(YELLOW)Prerequisites:$(NC)"
	@echo "  - kubectl configured and connected to cluster"
	@echo "  - Updated secrets in k8s/secret.yaml"
	@echo "  - Persistent Volume support in cluster"
	@echo ""
	@echo "$(YELLOW)Quick Start:$(NC)"
	@echo "  1. Update secrets: edit k8s/secret.yaml"
	@echo "  2. Deploy: make k8s-deploy"
	@echo "  3. Check status: make k8s-status"
	@echo "  4. Access: make k8s-port-forward"

# Verification and testing commands
verify: ## Run comprehensive verification of all core flows
	@echo "$(BLUE)Running comprehensive verification...$(NC)"
	python scripts/final_verification.py

smoke-test: ## Run basic smoke test
	@echo "$(BLUE)Running smoke test...$(NC)"
	python scripts/simple_test.py

verify-detailed: ## Run detailed verification with full report
	@echo "$(BLUE)Running detailed verification...$(NC)"
	python scripts/comprehensive_verification.py

start-server: ## Start the development server
	@echo "$(BLUE)Starting FastAPI server...$(NC)"
	python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

verify-full: start-server verify ## Start server and run full verification
	@echo "$(GREEN)Full verification complete!$(NC)"

help-verify: ## Verification and testing help
	@echo "$(BLUE)Verification Commands:$(NC)"
	@echo "  make verify          - Run comprehensive verification"
	@echo "  make smoke-test      - Quick smoke test"
	@echo "  make verify-detailed - Detailed verification with report"
	@echo "  make start-server    - Start development server"
	@echo "  make verify-full     - Start server and verify"
	@echo ""
	@echo "$(YELLOW)What gets tested:$(NC)"
	@echo "  • Authentication flow (register/login/protected routes)"
	@echo "  • Expense management (create/list/pagination)"
	@echo "  • Budget management (create/list)"
	@echo "  • Receipt upload and OCR processing"
	@echo "  • OpenAPI documentation (/docs, /redoc)"
	@echo "  • Response models and error handling"
	@echo "  • No stack traces in error responses"
	@echo ""
	@echo "$(YELLOW)Reports:$(NC)"
	@echo "  • See VERIFICATION_REPORT.md for detailed results"
	@echo "  • API docs: http://localhost:8000/docs"

# Performance testing commands
perf-baseline: ## Run performance baseline tests
	@echo "$(BLUE)Running performance baseline tests...$(NC)"
	python tests/performance/baseline_test.py --output performance_baseline.json

perf-load: ## Run Locust load testing (interactive)
	@echo "$(BLUE)Starting Locust load testing...$(NC)"
	@echo "$(YELLOW)Open http://localhost:8089 to configure and start tests$(NC)"
	locust -f tests/load/locustfile.py --host=http://localhost:8000

perf-load-headless: ## Run Locust load testing (headless, 5 min)
	@echo "$(BLUE)Running headless load test...$(NC)"
	locust -f tests/load/locustfile.py --host=http://localhost:8000 \
		--users 25 --spawn-rate 5 --run-time 5m --headless

perf-load-stress: ## Run stress test (high load, 2 min)
	@echo "$(BLUE)Running stress test...$(NC)"
	locust -f tests/load/locustfile.py --host=http://localhost:8000 \
		HeavyloadUser --users 50 --spawn-rate 10 --run-time 2m --headless

perf-health: ## Test health and monitoring endpoints
	@echo "$(BLUE)Testing health endpoints...$(NC)"
	@echo "Health check:"
	@curl -s http://localhost:8000/healthz | jq . || echo "Health endpoint not available"
	@echo "\nReadiness check:"
	@curl -s http://localhost:8000/readyz | jq . || echo "Readiness endpoint not available"
	@echo "\nSLO status:"
	@curl -s http://localhost:8000/slo | jq . || echo "SLO endpoint not available"

help-perf: ## Performance testing help
	@echo "$(BLUE)Performance Testing Commands:$(NC)"
	@echo "  make perf-baseline      - Run performance baseline tests"
	@echo "  make perf-load          - Interactive Locust load testing"
	@echo "  make perf-load-headless - Automated load test (5 min)"
	@echo "  make perf-load-stress   - High-load stress test (2 min)"
	@echo "  make perf-health        - Test health/monitoring endpoints"
	@echo ""
	@echo "$(YELLOW)Performance Targets (SLOs):$(NC)"
	@echo "  • P95 response time < 300ms (GET /expenses)"
	@echo "  • P99 response time < 1000ms (all endpoints)"
	@echo "  • Error rate < 1% (5xx errors)"
	@echo "  • Service availability > 99.9%"
	@echo "  • Database connection time < 100ms"
	@echo ""
	@echo "$(YELLOW)Monitoring Endpoints:$(NC)"
	@echo "  • GET /healthz  - Basic health check"
	@echo "  • GET /readyz   - Readiness check (includes DB)"
	@echo "  • GET /metrics  - Detailed system metrics"
	@echo "  • GET /slo      - Service Level Objectives status"
	@echo ""
	@echo "$(YELLOW)Load Testing Types:$(NC)"
	@echo "  • ExpenseTrackerUser - Normal usage patterns"
	@echo "  • LightloadUser      - Read-heavy operations"
	@echo "  • HeavyloadUser      - Write-heavy stress testing"
	@echo ""
	@echo "$(YELLOW)Reports:$(NC)"
	@echo "  • Performance results: performance_baseline.json"
	@echo "  • Detailed guide: PERFORMANCE_REPORT.md"

# Security commands
security-scan: ## Run comprehensive security scans
	@echo "$(BLUE)Running comprehensive security scan...$(NC)"
	python scripts/security_scan.py --output security_results.json

security-audit: ## Run dependency vulnerability audit
	@echo "$(BLUE)Running dependency audit...$(NC)"
	@python -m pip_audit --requirement requirements.txt || echo "$(YELLOW)pip-audit not installed$(NC)"

security-bandit: ## Run static security analysis
	@echo "$(BLUE)Running static security analysis...$(NC)"
	@python -m bandit -r app/ -f json -ll || echo "$(YELLOW)bandit not installed$(NC)"

security-safety: ## Check for known vulnerabilities
	@echo "$(BLUE)Checking for known vulnerabilities...$(NC)"
	@python -m safety check --requirement requirements.txt || echo "$(YELLOW)safety not installed$(NC)"

security-install: ## Install security scanning tools
	@echo "$(BLUE)Installing security tools...$(NC)"
	pip install pip-audit bandit safety

security-fix: ## Generate secure configuration
	@echo "$(BLUE)Generating secure configuration...$(NC)"
	@echo "SECRET_KEY=$$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
	@echo "JWT_KEY_ID=$$(date +%Y%m%d)"
	@echo "Copy env.example to .env and update with secure values"

# Database and migration commands
migrate-init: ## Initialize Alembic migrations
	@echo "$(BLUE)Initializing Alembic migrations...$(NC)"
	python -m alembic init alembic

migrate-generate: ## Generate new migration
	@echo "$(BLUE)Generating new migration...$(NC)"
	python -m alembic revision --autogenerate -m "$(MESSAGE)"

migrate-upgrade: ## Apply pending migrations
	@echo "$(BLUE)Applying migrations...$(NC)"
	python -m alembic upgrade head

migrate-downgrade: ## Downgrade one migration
	@echo "$(BLUE)Downgrading migration...$(NC)"
	python -m alembic downgrade -1

migrate-history: ## Show migration history
	@echo "$(BLUE)Migration history:$(NC)"
	python -m alembic history

# Backup and restore commands
backup: ## Create database backup
	@echo "$(BLUE)Creating database backup...$(NC)"
	python scripts/database_backup.py backup

backup-compressed: ## Create compressed database backup
	@echo "$(BLUE)Creating compressed database backup...$(NC)"
	python scripts/database_backup.py backup --compress

backup-list: ## List available backups
	@echo "$(BLUE)Available backups:$(NC)"
	python scripts/database_backup.py list

backup-cleanup: ## Clean up old backups
	@echo "$(BLUE)Cleaning up old backups...$(NC)"
	python scripts/database_backup.py cleanup

backup-restore: ## Restore from backup (requires BACKUP_FILE variable)
	@echo "$(BLUE)Restoring from backup: $(BACKUP_FILE)$(NC)"
	python scripts/database_backup.py restore $(BACKUP_FILE)

# Demo data commands
demo-seed: ## Seed demo data
	@echo "$(BLUE)Seeding demo data...$(NC)"
	python scripts/seed_demo_data.py --users 5 --days 90

demo-seed-large: ## Seed large demo dataset
	@echo "$(BLUE)Seeding large demo dataset...$(NC)"
	python scripts/seed_demo_data.py --users 20 --days 365 --expenses-per-day 4

demo-clear: ## Clear demo data
	@echo "$(BLUE)Clearing demo data...$(NC)"
	python scripts/seed_demo_data.py --clear-only

demo-summary: ## Show demo data summary
	@echo "$(BLUE)Demo data summary:$(NC)"
	python scripts/seed_demo_data.py --summary

# Data management and retention
data-export: ## Export user data (requires USER_ID)
	@echo "$(BLUE)Exporting user data...$(NC)"
	@echo "Use the /data/export endpoint via API"

data-retention-check: ## Check data retention status
	@echo "$(BLUE)Checking data retention status...$(NC)"
	@echo "Use the /data/retention-stats endpoint via API"

data-cleanup-dry: ## Dry run of data cleanup
	@echo "$(BLUE)Running data cleanup dry run...$(NC)"
	@echo "Use the /data/admin/cleanup?dry_run=true endpoint via API"

# Observability and monitoring commands
logs-json: ## Start with JSON structured logging
	@echo "$(BLUE)Starting server with JSON logging...$(NC)"
	JSON_LOGS=true LOG_LEVEL=INFO python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

logs-console: ## Start with console logging (development)
	@echo "$(BLUE)Starting server with console logging...$(NC)"
	JSON_LOGS=false LOG_LEVEL=DEBUG python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

metrics-check: ## Check metrics endpoint
	@echo "$(BLUE)Checking metrics endpoint...$(NC)"
	@curl -s http://localhost:8000/metrics | head -20 || echo "$(YELLOW)Server not running or metrics unavailable$(NC)"

metrics-health: ## Check metrics system health
	@echo "$(BLUE)Checking metrics health...$(NC)"
	@curl -s http://localhost:8000/monitoring/health/metrics | jq . || echo "$(YELLOW)Server not running or metrics unavailable$(NC)"

monitoring-debug: ## Get monitoring debug info (requires admin auth)
	@echo "$(BLUE)Getting monitoring debug info...$(NC)"
	@echo "$(YELLOW)Note: Requires admin authentication$(NC)"
	@echo "curl -H 'Authorization: Bearer \$$ADMIN_TOKEN' http://localhost:8000/monitoring/debug/metrics"

observability-test: ## Test observability endpoints
	@echo "$(BLUE)Testing observability endpoints...$(NC)"
	@echo "Testing metrics endpoint:"
	@curl -s -o /dev/null -w "Status: %{http_code}, Time: %{time_total}s\n" http://localhost:8000/metrics
	@echo "Testing health endpoint:"
	@curl -s -o /dev/null -w "Status: %{http_code}, Time: %{time_total}s\n" http://localhost:8000/healthz
	@echo "Testing monitoring health:"
	@curl -s -o /dev/null -w "Status: %{http_code}, Time: %{time_total}s\n" http://localhost:8000/monitoring/health/metrics

install-monitoring: ## Install monitoring dependencies
	@echo "$(BLUE)Installing monitoring dependencies...$(NC)"
	pip install structlog prometheus-client sentry-sdk[fastapi] python-json-logger pythonjsonlogger

help-security: ## Security scanning and hardening help
	@echo "$(BLUE)Security Commands:$(NC)"
	@echo "  make security-scan      - Run comprehensive security scan"
	@echo "  make security-audit     - Run dependency vulnerability audit"
	@echo "  make security-bandit    - Run static security analysis"
	@echo "  make security-safety    - Check for known vulnerabilities"
	@echo "  make security-install   - Install security scanning tools"
	@echo "  make security-fix       - Generate secure configuration"
	@echo ""
	@echo "$(YELLOW)Security Features Implemented:$(NC)"
	@echo "  ✅ CORS restricted to known origins"
	@echo "  ✅ Security headers (CSP, X-Frame-Options, etc.)"
	@echo "  ✅ Rate limiting on auth & write endpoints"
	@echo "  ✅ JWT with expiry/refresh & key rotation"
	@echo "  ✅ HTTPS enforcement & secure cookies"
	@echo "  ✅ Dependency vulnerability scanning"
	@echo ""
	@echo "$(YELLOW)Security Scans:$(NC)"
	@echo "  • pip-audit  - Check dependencies for known CVEs"
	@echo "  • bandit     - Static analysis for Python security issues"
	@echo "  • safety     - Check against PyUp.io vulnerability database"
	@echo "  • Config validation - Check security configuration"
	@echo ""
	@echo "$(YELLOW)Production Security Checklist:$(NC)"
	@echo "  1. Set ENVIRONMENT=production in .env"
	@echo "  2. Generate strong SECRET_KEY (make security-fix)"
	@echo "  3. Set HTTPS_ONLY=true"
	@echo "  4. Configure CORS_ORIGINS with your domains"
	@echo "  5. Enable SECURE_COOKIES=true"
	@echo "  6. Run security scans regularly"
	@echo ""
	@echo "$(YELLOW)Reports:$(NC)"
	@echo "  • Security scan results: security_results.json"
	@echo "  • Configuration template: env.example"
