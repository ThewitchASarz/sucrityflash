"""
Scopes API - BFF Proxy to SecurityFlash V1

Scopes are nested under projects in V1: /api/v1/projects/{project_id}/scopes
FastAPI doesn't support path params in router prefix, so we include the full path in each route.
"""
from fastapi import APIRouter, Request, Depends
from api.proxy import get_proxy, SecurityFlashProxy

router = APIRouter(tags=["Scopes"])

# List scopes for a project
@router.get("/api/v1/projects/{project_id}/scopes")
async def list_scopes(project_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/projects/{project_id}/scopes")

# Create scope for a project
@router.post("/api/v1/projects/{project_id}/scopes")
async def create_scope(project_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/projects/{project_id}/scopes")

# Get specific scope
@router.get("/api/v1/projects/{project_id}/scopes/{scope_id}")
async def get_scope(project_id: str, scope_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/projects/{project_id}/scopes/{scope_id}")

# Update scope
@router.put("/api/v1/projects/{project_id}/scopes/{scope_id}")
async def update_scope(project_id: str, scope_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/projects/{project_id}/scopes/{scope_id}")

# Delete scope
@router.delete("/api/v1/projects/{project_id}/scopes/{scope_id}")
async def delete_scope(project_id: str, scope_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/projects/{project_id}/scopes/{scope_id}")

# Lock scope (required before starting run)
@router.post("/api/v1/projects/{project_id}/scopes/{scope_id}/lock")
async def lock_scope(project_id: str, scope_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/projects/{project_id}/scopes/{scope_id}/lock")
