"""
Approvals API - BFF Proxy to SecurityFlash V1
V1 uses: /api/v1/runs/{run_id}/approvals/pending
"""
from fastapi import APIRouter, Request, Depends
from api.proxy import get_proxy, SecurityFlashProxy

router = APIRouter()

# Get pending approvals for a run
@router.get("/api/v1/runs/{run_id}/approvals/pending")
async def get_pending_approvals(run_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/runs/{run_id}/approvals/pending")

# Approve an action
@router.post("/api/v1/runs/{run_id}/approvals/{action_id}/approve")
async def approve_action(run_id: str, action_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/runs/{run_id}/approvals/{action_id}/approve")

# Reject an action
@router.post("/api/v1/runs/{run_id}/approvals/{action_id}/reject")
async def reject_action(run_id: str, action_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/runs/{run_id}/approvals/{action_id}/reject")
