.PHONY: help install docker-up docker-down migrate migrate-create api worker agent reviewer test clean

help:
	@echo "SecurityFlash V1 Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install Python dependencies"
	@echo "  make docker-up     Start infrastructure (Postgres, Redis, MinIO)"
	@echo "  make docker-down   Stop infrastructure"
	@echo "  make migrate       Run database migrations"
	@echo ""
	@echo "Run Services (3 separate terminals):"
	@echo "  make api           Start Control Plane (FastAPI)"
	@echo "  make worker        Start Worker Runtime"
	@echo "  make agent RUN_ID=<uuid>  Start Agent Runtime"
	@echo ""
	@echo "Human Interface:"
	@echo "  make reviewer-queue RUN_ID=<uuid>  Show pending approvals"
	@echo "  make reviewer-approve RUN_ID=<uuid> ACTION_ID=<uuid>  Approve action"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         Clean Python cache files"

install:
	@echo "Installing dependencies with Poetry..."
	poetry install

docker-up:
	@echo "Starting infrastructure services..."
	docker-compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@echo "✅ Infrastructure ready (Postgres, Redis, MinIO)"

docker-down:
	@echo "Stopping infrastructure services..."
	docker-compose down

migrate:
	@echo "Running database migrations..."
	alembic upgrade head

migrate-create:
	@echo "Creating new migration..."
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

api:
	@echo "Starting Control Plane (FastAPI)..."
	@echo "CRITICAL: This runtime must NEVER instantiate agents or execute tools"
	python -m uvicorn apps.api.main:app --reload

worker:
	@echo "Starting Worker Runtime..."
	@echo "MUST-FIX D: Resource limits enforced (CPU 1.0, Memory 512M)"
	python -m apps.workers.runner

agent:
	@if [ -z "$(RUN_ID)" ]; then \
		echo "Error: RUN_ID required. Usage: make agent RUN_ID=<uuid>"; \
		exit 1; \
	fi
	@echo "Starting Agent Runtime for run $(RUN_ID)..."
	@echo "MUST-FIX E: V1 = Python only, n8n excluded"
	python -m apps.agents.runner $(RUN_ID)

reviewer-queue:
	@if [ -z "$(RUN_ID)" ]; then \
		echo "Error: RUN_ID required. Usage: make reviewer-queue RUN_ID=<uuid>"; \
		exit 1; \
	fi
	python scripts/reviewer_queue.py queue --run-id $(RUN_ID)

reviewer-approve:
	@if [ -z "$(RUN_ID)" ] || [ -z "$(ACTION_ID)" ]; then \
		echo "Error: RUN_ID and ACTION_ID required."; \
		echo "Usage: make reviewer-approve RUN_ID=<uuid> ACTION_ID=<uuid>"; \
		exit 1; \
	fi
	python scripts/reviewer_queue.py approve --action-id $(ACTION_ID) --run-id $(RUN_ID)

test:
	@echo "Running tests..."
	pytest apps/api/tests/ -v

clean:
	@echo "Cleaning Python cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "✅ Clean complete"
