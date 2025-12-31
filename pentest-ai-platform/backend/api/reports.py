"""
Reports API - BFF Proxy to SecurityFlash V1
"""
from fastapi import APIRouter, Request, Depends
from api.proxy import get_proxy, SecurityFlashProxy

router = APIRouter()

@router.post("")
async def create_report(request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, "/api/v1/reports")

@router.get("/{report_id}")
async def get_report(report_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/reports/{report_id}")
