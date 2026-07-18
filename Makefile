# ─────────────────────────────────────────────────────────────────────────────
# Atlas AI — Makefile
#
# Usage:
#   make help        Show all available targets
#   make setup       Install all local tooling prerequisites
#   make dev         Start local dev stack via docker-compose
#   make build       Build Docker images
#   make push        Push images to registry
#   make deploy      Apply all Kubernetes manifests
#   make undeploy    Tear down all Kubernetes resources
#   make logs        Stream backend logs
#   make test        Run all test suites
#   make lint        Run linters (ruff, mypy, eslint)
#   make seed-demo   Seed demo incidents into local DB
# ─────────────────────────────────────────────────────────────────────────────

SHELL := /bin/bash
.DEFAULT_GOAL := help

# ── Image configuration ───────────────────────────────────────────────────────
REGISTRY          ?= ghcr.io/company
IMAGE_BACKEND     ?= $(REGISTRY)/atlas-ai-backend
IMAGE_FRONTEND    ?= $(REGISTRY)/atlas-ai-frontend
TAG               ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo "latest")
TAG_LATEST        ?= latest

# ── Kubernetes configuration ──────────────────────────────────────────────────
NAMESPACE         ?= atlas-ai
KUBE_CONTEXT      ?= $(shell kubectl config current-context 2>/dev/null || echo "default")
MANIFESTS_DIR     := k8s

# ── Tool paths ────────────────────────────────────────────────────────────────
KUBECTL           := kubectl --context=$(KUBE_CONTEXT)
DOCKER            := docker
COMPOSE           := docker compose

# ── Colors ────────────────────────────────────────────────────────────────────
BOLD  := \033[1m
GREEN := \033[32m
BLUE  := \033[34m
CYAN  := \033[36m
RESET := \033[0m

# ─────────────────────────────────────────────────────────────────────────────
# HELP
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: help
help: ## Show this help message
	@echo ""
	@printf "$(BOLD)$(BLUE)╔══════════════════════════════════════════════════════╗$(RESET)\n"
	@printf "$(BOLD)$(BLUE)║          Atlas AI — Platform Makefile                ║$(RESET)\n"
	@printf "$(BOLD)$(BLUE)╚══════════════════════════════════════════════════════╝$(RESET)\n"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-22s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@printf "  $(BOLD)IMAGE_BACKEND:$(RESET)  $(IMAGE_BACKEND):$(TAG)\n"
	@printf "  $(BOLD)IMAGE_FRONTEND:$(RESET) $(IMAGE_FRONTEND):$(TAG)\n"
	@printf "  $(BOLD)NAMESPACE:$(RESET)      $(NAMESPACE)\n"
	@printf "  $(BOLD)KUBE_CONTEXT:$(RESET)   $(KUBE_CONTEXT)\n"
	@echo ""

# ─────────────────────────────────────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: setup
setup: ## Install all local dev prerequisites (Python, Node, tools)
	@printf "$(GREEN)▶ Checking prerequisites...$(RESET)\n"
	@command -v docker     >/dev/null 2>&1 || { echo "ERROR: docker not found"; exit 1; }
	@command -v kubectl    >/dev/null 2>&1 || { echo "ERROR: kubectl not found"; exit 1; }
	@command -v python3    >/dev/null 2>&1 || { echo "ERROR: python3 not found"; exit 1; }
	@command -v node       >/dev/null 2>&1 || { echo "ERROR: node not found"; exit 1; }
	@printf "$(GREEN)▶ Setting up Python virtual environment...$(RESET)\n"
	cd backend && python3 -m venv .venv && \
		source .venv/bin/activate && \
		pip install --upgrade pip && \
		pip install -r requirements.txt -r requirements-dev.txt
	@printf "$(GREEN)▶ Installing frontend dependencies...$(RESET)\n"
	cd frontend && npm ci
	@printf "$(GREEN)▶ Creating .env from .env.example (if not exists)...$(RESET)\n"
	@test -f .env || cp .env.example .env
	@printf "$(GREEN)✔ Setup complete! Edit .env then run: make dev$(RESET)\n"

.PHONY: setup-k8s-tools
setup-k8s-tools: ## Install Helm, kubectx, k9s, stern (macOS via Homebrew)
	@printf "$(GREEN)▶ Installing Kubernetes tooling via Homebrew...$(RESET)\n"
	brew install helm kubectx k9s stern kubecolor
	@printf "$(GREEN)✔ Kubernetes tools installed$(RESET)\n"

# ─────────────────────────────────────────────────────────────────────────────
# LOCAL DEVELOPMENT
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: dev
dev: ## Start full local dev stack (postgres, redis, backend, frontend, prometheus, grafana)
	@printf "$(GREEN)▶ Starting Atlas AI local dev stack...$(RESET)\n"
	$(COMPOSE) up --build --remove-orphans

.PHONY: dev-bg
dev-bg: ## Start dev stack in background
	@printf "$(GREEN)▶ Starting Atlas AI stack in background...$(RESET)\n"
	$(COMPOSE) up --build --remove-orphans -d
	@printf "$(GREEN)✔ Stack running. Services:$(RESET)\n"
	@printf "   Backend:    http://localhost:8000  (API docs: /docs)\n"
	@printf "   Frontend:   http://localhost:3000\n"
	@printf "   Prometheus: http://localhost:9091\n"
	@printf "   Grafana:    http://localhost:3001  (admin/admin)\n"

.PHONY: dev-stop
dev-stop: ## Stop all local dev services
	$(COMPOSE) down

.PHONY: dev-clean
dev-clean: ## Stop services and remove volumes (DESTRUCTIVE — deletes local DB data)
	@printf "$(BOLD)WARNING: This will delete all local PostgreSQL and Redis data. Continue? [y/N] $(RESET)" && \
		read ans && [ $${ans:-N} = y ]
	$(COMPOSE) down --volumes --remove-orphans

.PHONY: dev-reset
dev-reset: dev-clean dev seed-demo ## Full reset: clean + restart + seed demo data

# ─────────────────────────────────────────────────────────────────────────────
# BUILD
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: build
build: build-backend build-frontend ## Build all Docker images

.PHONY: build-backend
build-backend: ## Build the backend Docker image
	@printf "$(GREEN)▶ Building backend image: $(IMAGE_BACKEND):$(TAG)$(RESET)\n"
	$(DOCKER) build \
		--target production \
		--platform linux/amd64 \
		--build-arg BUILD_DATE=$(shell date -u +%Y-%m-%dT%H:%M:%SZ) \
		--build-arg VCS_REF=$(TAG) \
		--build-arg VERSION=$(TAG) \
		-t $(IMAGE_BACKEND):$(TAG) \
		-t $(IMAGE_BACKEND):$(TAG_LATEST) \
		./backend
	@printf "$(GREEN)✔ Backend image built$(RESET)\n"

.PHONY: build-frontend
build-frontend: ## Build the frontend Docker image
	@printf "$(GREEN)▶ Building frontend image: $(IMAGE_FRONTEND):$(TAG)$(RESET)\n"
	$(DOCKER) build \
		--target production \
		--platform linux/amd64 \
		--build-arg BUILD_DATE=$(shell date -u +%Y-%m-%dT%H:%M:%SZ) \
		--build-arg VCS_REF=$(TAG) \
		--build-arg VERSION=$(TAG) \
		-t $(IMAGE_FRONTEND):$(TAG) \
		-t $(IMAGE_FRONTEND):$(TAG_LATEST) \
		./frontend
	@printf "$(GREEN)✔ Frontend image built$(RESET)\n"

# ─────────────────────────────────────────────────────────────────────────────
# PUSH
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: push
push: push-backend push-frontend ## Push all images to registry

.PHONY: push-backend
push-backend: build-backend ## Build and push backend image
	@printf "$(GREEN)▶ Pushing $(IMAGE_BACKEND):$(TAG)...$(RESET)\n"
	$(DOCKER) push $(IMAGE_BACKEND):$(TAG)
	$(DOCKER) push $(IMAGE_BACKEND):$(TAG_LATEST)
	@printf "$(GREEN)✔ Backend pushed$(RESET)\n"

.PHONY: push-frontend
push-frontend: build-frontend ## Build and push frontend image
	@printf "$(GREEN)▶ Pushing $(IMAGE_FRONTEND):$(TAG)...$(RESET)\n"
	$(DOCKER) push $(IMAGE_FRONTEND):$(TAG)
	$(DOCKER) push $(IMAGE_FRONTEND):$(TAG_LATEST)
	@printf "$(GREEN)✔ Frontend pushed$(RESET)\n"

# ─────────────────────────────────────────────────────────────────────────────
# KUBERNETES DEPLOY
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: deploy
deploy: ## Apply all Kubernetes manifests in dependency order
	@printf "$(GREEN)▶ Deploying Atlas AI to namespace: $(NAMESPACE) (context: $(KUBE_CONTEXT))$(RESET)\n"
	@printf "$(BOLD)Confirm deploy to context '$(KUBE_CONTEXT)'? [y/N] $(RESET)" && \
		read ans && [ $${ans:-N} = y ]
	# 1. Namespace
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/namespace.yaml
	# 2. RBAC
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/rbac/serviceaccount.yaml
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/rbac/clusterrole.yaml
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/rbac/clusterrolebinding.yaml
	# 3. Secrets & ConfigMap
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/secrets.yaml
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/configmap.yaml
	# 4. Storage — PostgreSQL
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/postgres/pvc.yaml
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/postgres/deployment.yaml
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/postgres/service.yaml
	# 5. Storage — Redis
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/redis/deployment.yaml
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/redis/service.yaml
	# 6. Wait for datastores to be ready
	@printf "$(GREEN)▶ Waiting for PostgreSQL...$(RESET)\n"
	$(KUBECTL) rollout status statefulset/postgres -n $(NAMESPACE) --timeout=120s
	@printf "$(GREEN)▶ Waiting for Redis...$(RESET)\n"
	$(KUBECTL) rollout status statefulset/redis -n $(NAMESPACE) --timeout=120s
	# 7. Backend
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/backend/deployment.yaml
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/backend/service.yaml
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/backend/hpa.yaml
	# 8. Frontend
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/frontend/deployment.yaml
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/frontend/service.yaml
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/frontend/hpa.yaml
	# 9. Ingress
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/ingress.yaml
	# 10. Monitoring
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/monitoring/prometheus.yaml
	# 11. Wait for backend rollout
	@printf "$(GREEN)▶ Waiting for backend rollout...$(RESET)\n"
	$(KUBECTL) rollout status deployment/atlas-ai-backend -n $(NAMESPACE) --timeout=180s
	$(KUBECTL) rollout status deployment/atlas-ai-frontend -n $(NAMESPACE) --timeout=120s
	@printf "$(GREEN)✔ Atlas AI deployed successfully!$(RESET)\n"
	@$(MAKE) status

.PHONY: deploy-dry-run
deploy-dry-run: ## Dry-run all manifests (validate without applying)
	@printf "$(GREEN)▶ Dry-run validating manifests...$(RESET)\n"
	$(KUBECTL) apply --dry-run=server -f $(MANIFESTS_DIR)/namespace.yaml
	$(KUBECTL) apply --dry-run=server -f $(MANIFESTS_DIR)/rbac/
	$(KUBECTL) apply --dry-run=server -f $(MANIFESTS_DIR)/configmap.yaml
	$(KUBECTL) apply --dry-run=server -f $(MANIFESTS_DIR)/postgres/
	$(KUBECTL) apply --dry-run=server -f $(MANIFESTS_DIR)/redis/
	$(KUBECTL) apply --dry-run=server -f $(MANIFESTS_DIR)/backend/
	$(KUBECTL) apply --dry-run=server -f $(MANIFESTS_DIR)/frontend/
	$(KUBECTL) apply --dry-run=server -f $(MANIFESTS_DIR)/ingress.yaml
	@printf "$(GREEN)✔ All manifests are valid$(RESET)\n"

.PHONY: undeploy
undeploy: ## Remove all Atlas AI resources from Kubernetes (DESTRUCTIVE)
	@printf "$(BOLD)WARNING: This will DELETE the entire '$(NAMESPACE)' namespace and ALL data.\n"
	@printf "Context: $(KUBE_CONTEXT)\nConfirm? [y/N] $(RESET)" && \
		read ans && [ $${ans:-N} = y ]
	$(KUBECTL) delete namespace $(NAMESPACE) --ignore-not-found
	$(KUBECTL) delete clusterrole atlas-ai-cluster-reader --ignore-not-found
	$(KUBECTL) delete clusterrolebinding atlas-ai-cluster-reader-binding --ignore-not-found
	@printf "$(GREEN)✔ Atlas AI undeployed$(RESET)\n"

.PHONY: upgrade-backend
upgrade-backend: build-backend push-backend ## Build, push, and rolling-restart backend
	@printf "$(GREEN)▶ Updating backend image tag to $(TAG)...$(RESET)\n"
	$(KUBECTL) set image deployment/atlas-ai-backend \
		backend=$(IMAGE_BACKEND):$(TAG) \
		-n $(NAMESPACE)
	$(KUBECTL) rollout status deployment/atlas-ai-backend -n $(NAMESPACE) --timeout=180s
	@printf "$(GREEN)✔ Backend upgraded$(RESET)\n"

.PHONY: upgrade-frontend
upgrade-frontend: build-frontend push-frontend ## Build, push, and rolling-restart frontend
	@printf "$(GREEN)▶ Updating frontend image tag to $(TAG)...$(RESET)\n"
	$(KUBECTL) set image deployment/atlas-ai-frontend \
		frontend=$(IMAGE_FRONTEND):$(TAG) \
		-n $(NAMESPACE)
	$(KUBECTL) rollout status deployment/atlas-ai-frontend -n $(NAMESPACE) --timeout=120s
	@printf "$(GREEN)✔ Frontend upgraded$(RESET)\n"

# ─────────────────────────────────────────────────────────────────────────────
# STATUS & LOGS
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: status
status: ## Show status of all Atlas AI pods
	@printf "$(BOLD)$(BLUE)── Atlas AI Kubernetes Status ──────────────────────────$(RESET)\n"
	$(KUBECTL) get pods,svc,ingress,hpa -n $(NAMESPACE) -o wide
	@printf "\n$(BOLD)$(BLUE)── HPA Status ───────────────────────────────────────────$(RESET)\n"
	$(KUBECTL) get hpa -n $(NAMESPACE)

.PHONY: logs
logs: ## Stream backend pod logs (use FILTER=error to grep)
	@printf "$(GREEN)▶ Streaming backend logs (Ctrl+C to stop)...$(RESET)\n"
ifdef FILTER
	$(KUBECTL) logs -n $(NAMESPACE) -l app.kubernetes.io/name=atlas-ai-backend \
		--all-containers --follow | grep -i "$(FILTER)"
else
	$(KUBECTL) logs -n $(NAMESPACE) -l app.kubernetes.io/name=atlas-ai-backend \
		--all-containers --follow --tail=100
endif

.PHONY: logs-frontend
logs-frontend: ## Stream frontend pod logs
	$(KUBECTL) logs -n $(NAMESPACE) -l app.kubernetes.io/name=atlas-ai-frontend \
		--all-containers --follow --tail=100

.PHONY: logs-postgres
logs-postgres: ## Stream Postgres logs
	$(KUBECTL) logs -n $(NAMESPACE) -l app.kubernetes.io/name=postgres --follow --tail=50

.PHONY: logs-redis
logs-redis: ## Stream Redis logs
	$(KUBECTL) logs -n $(NAMESPACE) -l app.kubernetes.io/name=redis --follow --tail=50

.PHONY: logs-local
logs-local: ## Stream backend logs in local docker-compose
	$(COMPOSE) logs -f backend

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: db-migrate
db-migrate: ## Run Alembic database migrations (local)
	@printf "$(GREEN)▶ Running database migrations...$(RESET)\n"
	cd backend && source .venv/bin/activate && \
		alembic upgrade head
	@printf "$(GREEN)✔ Migrations applied$(RESET)\n"

.PHONY: db-migrate-k8s
db-migrate-k8s: ## Run migrations via kubectl exec on backend pod
	@printf "$(GREEN)▶ Running migrations on Kubernetes...$(RESET)\n"
	$(KUBECTL) exec -n $(NAMESPACE) \
		$$($(KUBECTL) get pod -n $(NAMESPACE) \
			-l app.kubernetes.io/name=atlas-ai-backend \
			-o jsonpath='{.items[0].metadata.name}') \
		-- alembic upgrade head

.PHONY: db-shell
db-shell: ## Open psql shell to local postgres
	$(COMPOSE) exec postgres psql -U atlas_ai -d atlas_ai

.PHONY: db-shell-k8s
db-shell-k8s: ## Open psql shell on Kubernetes postgres pod
	$(KUBECTL) exec -it -n $(NAMESPACE) \
		$$($(KUBECTL) get pod -n $(NAMESPACE) \
			-l app.kubernetes.io/name=postgres \
			-o jsonpath='{.items[0].metadata.name}') \
		-- psql -U atlas_ai -d atlas_ai

.PHONY: db-backup
db-backup: ## Backup Kubernetes postgres to local file
	@BACKUP_FILE="backup_atlas_ai_$(shell date +%Y%m%d_%H%M%S).sql.gz" && \
	printf "$(GREEN)▶ Backing up to $$BACKUP_FILE...$(RESET)\n" && \
	$(KUBECTL) exec -n $(NAMESPACE) \
		$$($(KUBECTL) get pod -n $(NAMESPACE) \
			-l app.kubernetes.io/name=postgres \
			-o jsonpath='{.items[0].metadata.name}') \
		-- pg_dump -U atlas_ai atlas_ai | gzip > $$BACKUP_FILE && \
	printf "$(GREEN)✔ Backup saved to $$BACKUP_FILE$(RESET)\n"

# ─────────────────────────────────────────────────────────────────────────────
# TESTING
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: test
test: test-backend test-frontend ## Run all test suites

.PHONY: test-backend
test-backend: ## Run backend unit and integration tests
	@printf "$(GREEN)▶ Running backend tests...$(RESET)\n"
	cd backend && source .venv/bin/activate && \
		pytest tests/ \
			--cov=app \
			--cov-report=term-missing \
			--cov-report=html:htmlcov \
			--cov-fail-under=80 \
			-v \
			--tb=short \
			-x
	@printf "$(GREEN)✔ Backend tests passed$(RESET)\n"

.PHONY: test-backend-watch
test-backend-watch: ## Run backend tests in watch mode
	cd backend && source .venv/bin/activate && \
		pytest-watch -- tests/ -v --tb=short

.PHONY: test-frontend
test-frontend: ## Run frontend unit tests
	@printf "$(GREEN)▶ Running frontend tests...$(RESET)\n"
	cd frontend && npm run test -- --watchAll=false --coverage
	@printf "$(GREEN)✔ Frontend tests passed$(RESET)\n"

.PHONY: test-e2e
test-e2e: ## Run end-to-end tests with Playwright (requires running stack)
	@printf "$(GREEN)▶ Running E2E tests...$(RESET)\n"
	cd frontend && npm run test:e2e
	@printf "$(GREEN)✔ E2E tests passed$(RESET)\n"

.PHONY: test-integration
test-integration: ## Run integration tests against local docker-compose stack
	@printf "$(GREEN)▶ Running integration tests...$(RESET)\n"
	cd backend && source .venv/bin/activate && \
		pytest tests/integration/ \
			--cov=app \
			-v \
			--tb=short \
			-m integration
	@printf "$(GREEN)✔ Integration tests passed$(RESET)\n"

# ─────────────────────────────────────────────────────────────────────────────
# LINTING & FORMATTING
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: lint
lint: lint-backend lint-frontend ## Run all linters

.PHONY: lint-backend
lint-backend: ## Lint backend (ruff + mypy)
	@printf "$(GREEN)▶ Linting backend...$(RESET)\n"
	cd backend && source .venv/bin/activate && \
		ruff check app/ tests/ && \
		mypy app/ --ignore-missing-imports --strict
	@printf "$(GREEN)✔ Backend lint passed$(RESET)\n"

.PHONY: lint-frontend
lint-frontend: ## Lint frontend (ESLint + TypeScript)
	@printf "$(GREEN)▶ Linting frontend...$(RESET)\n"
	cd frontend && npm run lint && npm run typecheck
	@printf "$(GREEN)✔ Frontend lint passed$(RESET)\n"

.PHONY: format
format: ## Auto-format all code (ruff + prettier)
	@printf "$(GREEN)▶ Formatting backend...$(RESET)\n"
	cd backend && source .venv/bin/activate && \
		ruff format app/ tests/ && \
		ruff check --fix app/ tests/
	@printf "$(GREEN)▶ Formatting frontend...$(RESET)\n"
	cd frontend && npm run format
	@printf "$(GREEN)✔ Formatting complete$(RESET)\n"

.PHONY: lint-k8s
lint-k8s: ## Lint Kubernetes manifests (kubeval + kube-score)
	@printf "$(GREEN)▶ Validating Kubernetes manifests...$(RESET)\n"
	@command -v kubeval >/dev/null 2>&1 && \
		find k8s -name "*.yaml" | xargs kubeval --strict || \
		echo "kubeval not found — skipping"
	@command -v kube-score >/dev/null 2>&1 && \
		find k8s -name "*.yaml" | xargs kube-score score || \
		echo "kube-score not found — skipping"
	@printf "$(GREEN)✔ Kubernetes manifest validation complete$(RESET)\n"

# ─────────────────────────────────────────────────────────────────────────────
# DEMO
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: seed-demo
seed-demo: ## Seed demo incidents, runbooks, and knowledge base into local DB
	@printf "$(GREEN)▶ Seeding demo data...$(RESET)\n"
	cd backend && source .venv/bin/activate && \
		python scripts/seed_demo.py \
			--incidents 20 \
			--runbooks 10 \
			--with-resolutions
	@printf "$(GREEN)✔ Demo data seeded$(RESET)\n"
	@printf "   Sample incidents created. Visit http://localhost:3000\n"

.PHONY: demo-incident
demo-incident: ## Trigger a live demo incident investigation via the API
	@printf "$(GREEN)▶ Triggering demo incident...$(RESET)\n"
	curl -s -X POST http://localhost:8000/api/v1/investigations \
		-H "Content-Type: application/json" \
		-d '{ \
			"title": "High latency detected on payment-service", \
			"severity": "P1", \
			"description": "P99 latency for /api/checkout spiked to 8s. Error rate 12%. Alerts firing: PaymentServiceHighLatency, PaymentServiceErrorRate.", \
			"affected_service": "payment-service", \
			"namespace": "production", \
			"labels": {"team": "payments", "env": "production"} \
		}' | python3 -m json.tool
	@printf "$(GREEN)✔ Demo incident triggered. Check the frontend for the live investigation.$(RESET)\n"

.PHONY: demo-tour
demo-tour: ## Print the step-by-step demo tour instructions
	@cat docs/demo-tour.md 2>/dev/null || printf "$(GREEN)\
	Demo Tour:\n\
	1. Visit http://localhost:3000 — Atlas AI Dashboard\n\
	2. Run: make demo-incident   — Trigger a live P1 incident\n\
	3. Watch the Orchestrator Agent triage & dispatch sub-agents\n\
	4. See diagnosis & proposed remediation in the UI\n\
	5. Approve or reject the remediation plan\n\
	6. View auto-generated post-mortem report\n\
	7. See Jira ticket + Slack notification (if configured)\n\
	8. Visit http://localhost:3001 for Grafana metrics\n\
	$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: shell-backend
shell-backend: ## Open a shell inside the running backend container (local)
	$(COMPOSE) exec backend bash

.PHONY: shell-backend-k8s
shell-backend-k8s: ## Open a shell inside the backend pod on Kubernetes
	$(KUBECTL) exec -it -n $(NAMESPACE) \
		$$($(KUBECTL) get pod -n $(NAMESPACE) \
			-l app.kubernetes.io/name=atlas-ai-backend \
			-o jsonpath='{.items[0].metadata.name}') \
		-- bash

.PHONY: port-forward
port-forward: ## Port-forward backend and frontend from Kubernetes to localhost
	@printf "$(GREEN)▶ Port-forwarding services (Ctrl+C to stop)...$(RESET)\n"
	$(KUBECTL) port-forward -n $(NAMESPACE) svc/atlas-ai-backend-service  8000:80 &
	$(KUBECTL) port-forward -n $(NAMESPACE) svc/atlas-ai-frontend-service 3000:80 &
	$(KUBECTL) port-forward -n $(NAMESPACE) svc/postgres-service          5432:5432 &
	wait

.PHONY: secrets-create
secrets-create: ## Apply secrets.yaml (use ONLY after replacing placeholder values!)
	@printf "$(BOLD)Have you replaced ALL placeholder values in k8s/secrets.yaml? [y/N] $(RESET)" && \
		read ans && [ $${ans:-N} = y ]
	$(KUBECTL) apply -f $(MANIFESTS_DIR)/secrets.yaml

.PHONY: version
version: ## Print current git tag and image tags
	@printf "Git SHA:         $(TAG)\n"
	@printf "Backend image:   $(IMAGE_BACKEND):$(TAG)\n"
	@printf "Frontend image:  $(IMAGE_FRONTEND):$(TAG)\n"

.PHONY: clean
clean: ## Remove local build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf frontend/.next frontend/out 2>/dev/null || true
	@printf "$(GREEN)✔ Clean complete$(RESET)\n"
