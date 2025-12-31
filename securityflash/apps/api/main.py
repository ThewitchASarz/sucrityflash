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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.api.core.logging import logger
from apps.api.routers import projects, scopes, runs, action_specs, approvals, evidence

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


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "control-plane"}


@app.on_event("startup")
async def startup():
    """Startup event."""
    logger.info("SecurityFlash Control Plane starting...")
    logger.info("CRITICAL: This runtime must NEVER instantiate agents or execute tools")
    logger.info("Agent Runtime: apps/agents/runner.py (separate process)")
    logger.info("Worker Runtime: apps/workers/runner.py (separate process)")


@app.on_event("shutdown")
async def shutdown():
    """Shutdown event."""
    logger.info("SecurityFlash Control Plane shutting down...")
