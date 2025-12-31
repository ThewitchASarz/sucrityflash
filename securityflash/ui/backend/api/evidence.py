"""
Evidence API - BFF Proxy to SecurityFlash V1
V1 uses: /api/v1/runs/{run_id}/evidence
"""
from fastapi import APIRouter, Request, Depends
from api.proxy import get_proxy, SecurityFlashProxy

router = APIRouter()

# List evidence for a run
@router.get("/api/v1/runs/{run_id}/evidence")
async def list_evidence(run_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/runs/{run_id}/evidence")

# Get specific evidence
@router.get("/api/v1/runs/{run_id}/evidence/{evidence_id}")
async def get_evidence(run_id: str, evidence_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/runs/{run_id}/evidence/{evidence_id}")

# Create evidence
@router.post("/api/v1/runs/{run_id}/evidence")
async def create_evidence(run_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/runs/{run_id}/evidence")

# Delete evidence (V1 will return 403 - evidence is immutable)
@router.delete("/api/v1/runs/{run_id}/evidence/{evidence_id}")
async def delete_evidence(run_id: str, evidence_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    """Proxy DELETE - V1 will return 403 (evidence is immutable)."""
    return await proxy.proxy_request(request, f"/api/v1/runs/{run_id}/evidence/{evidence_id}")
