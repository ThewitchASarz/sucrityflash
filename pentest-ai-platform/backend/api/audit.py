"""
Audit API - BFF Proxy to SecurityFlash V1
"""
from fastapi import APIRouter, Request, Depends
from api.proxy import get_proxy, SecurityFlashProxy

router = APIRouter()

@router.get("/logs")
async def get_audit_logs(request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, "/api/v1/audit/logs")

@router.post("/bundles")
async def create_audit_bundle(request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, "/api/v1/audit/bundles")
