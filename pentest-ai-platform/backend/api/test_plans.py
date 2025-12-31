"""
Test Plans API - BFF Proxy to SecurityFlash V1
"""
from fastapi import APIRouter, Request, Depends
from api.proxy import get_proxy, SecurityFlashProxy

router = APIRouter()

@router.get("")
async def list_test_plans(request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, "/api/v1/test-plans")

@router.post("")
async def create_test_plan(request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, "/api/v1/test-plans")

@router.get("/{plan_id}")
async def get_test_plan(plan_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/test-plans/{plan_id}")
