"""
SecurityFlash Control Plane (FastAPI).

CRITICAL ARCHITECTURAL CONSTRAINTS:
- This is the governance-only runtime
- NEVER instantiate agents or execute tools here
- NEVER run agents as background tasks
- All agent execution happens in apps/agents/runner.py (separate process)
- All tool execution happens in apps/workers/runner.py (separate process)

Responsibilities:
- Accept and validate ActionSpecs from agents (via POST)
- Route ActionSpecs to Policy Engine for evaluation
- Expose approval endpoints for human reviewers
- Store and serve evidence metadata (immutable)
- Enforce RBAC (no DELETE on evidence, no PATCH on locked scopes)
- Log all state transitions to audit_log

V1 Endpoints:
- POST   /api/v1/projects
- POST   /api/v1/projects/{project_id}/scopes
- POST   /api/v1/projects/{project_id}/scopes/{scope_id}/lock
- POST   /api/v1/projects/{project_id}/runs
- POST   /api/v1/runs/{run_id}/start (MUST-FIX A: explicit state transition)
- POST   /api/v1/runs/{run_id}/action-specs
- GET    /api/v1/runs/{run_id}/approvals/pending
- POST   /api/v1/runs/{run_id}/approvals/{action_id}/approve
- POST   /api/v1/runs/{run_id}/approvals/{action_id}/reject
- POST   /api/v1/runs/{run_id}/evidence
- GET    /api/v1/runs/{run_id}/evidence/{evidence_id}
- DELETE /api/v1/runs/{run_id}/evidence/{evidence_id} (always 403)
- GET    /api/v1/runs/{run_id}
- GET    /api/v1/runs/{run_id}/audit

Runtime Separation:
- Control Plane: THIS FILE (FastAPI, stateless)
- Agent Runtime: apps/agents/runner.py (separate Python process)
- Worker Runtime: apps/workers/runner.py (separate Python process)

Local dev: python -m uvicorn apps.api.main:app --reload
"""
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from apps.api.core.config import settings
from apps.api.core.logging import logger
from apps.api.routers import (
    action_specs,
    approvals,
    evidence,
    executions,
    findings,
    manual_validation_tasks,
    projects,
    runs,
    scopes,
    tools,
    validation_packs,
)
from apps.observability.metrics import CONTENT_TYPE_LATEST, generate_latest, update_redis_streams_lag

# Create FastAPI app
app = FastAPI(
    title="SecurityFlash Control Plane",
    description="Governed agentic penetration testing platform - Control Plane API",
    version="1.0.0"
)

# CORS middleware (configure for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router)
app.include_router(scopes.router)
app.include_router(runs.router)
app.include_router(evidence.router)  # Evidence before action_specs (more specific routes)
app.include_router(approvals.router)
app.include_router(action_specs.router, prefix="/api/v1/runs/{run_id}/action-specs")
app.include_router(action_specs.global_router)  # Global query endpoint for workers
app.include_router(tools.router, prefix="/api/v1")
app.include_router(executions.router)  # PHASE 2: Executions
app.include_router(findings.router)  # PHASE 2: Findings
app.include_router(manual_validation_tasks.router)  # PHASE 3: Manual Validation Tasks
app.include_router(validation_packs.router)  # PHASE 3: Validation Packs


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "control-plane"}


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.on_event("startup")
async def startup():
    """Startup event."""
    logger.info("SecurityFlash Control Plane starting...")
    logger.info("CRITICAL: This runtime must NEVER instantiate agents or execute tools")
    logger.info("Agent Runtime: apps/agents/runner.py (separate process)")
    logger.info("Worker Runtime: apps/workers/runner.py (separate process)")

    async def _redis_metrics_loop():
        stream_groups = [
            (settings.REDIS_STREAM_CONTROL_PLANE, settings.REDIS_STREAM_CONTROL_PLANE_GROUP),
            (settings.REDIS_STREAM_AGENT, settings.REDIS_STREAM_AGENT_GROUP),
            (settings.REDIS_STREAM_WORKER, settings.REDIS_STREAM_WORKER_GROUP),
        ]
        while True:
            await asyncio.to_thread(
                update_redis_streams_lag,
                settings.REDIS_URL,
                stream_groups,
            )
            await asyncio.sleep(settings.REDIS_METRICS_INTERVAL_SEC)

    app.state.redis_metrics_task = asyncio.create_task(_redis_metrics_loop())


@app.on_event("shutdown")
async def shutdown():
    """Shutdown event."""
    logger.info("SecurityFlash Control Plane shutting down...")
    task = getattr(app.state, "redis_metrics_task", None)
    if task:
        task.cancel()
