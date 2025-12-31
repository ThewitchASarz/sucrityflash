"""
Findings API - BFF Proxy to SecurityFlash V1
"""
from fastapi import APIRouter, Request, Depends
from api.proxy import get_proxy, SecurityFlashProxy

router = APIRouter()

@router.get("")
async def list_findings(request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, "/api/v1/findings")

@router.get("/{finding_id}")
async def get_finding(finding_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/findings/{finding_id}")
