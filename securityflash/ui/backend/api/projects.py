"""
Projects API - BFF Proxy to SecurityFlash V1

V2 DOES NOT store projects. All project data lives in SecurityFlash V1.
This router only proxies requests to V1.
"""
from fastapi import APIRouter, Request, Depends
from api.proxy import get_proxy, SecurityFlashProxy

router = APIRouter()


@router.get("")
async def list_projects(
    request: Request,
    proxy: SecurityFlashProxy = Depends(get_proxy)
):
    """Proxy: List projects from SecurityFlash V1."""
    return await proxy.proxy_request(request, "/api/v1/projects")


@router.post("")
async def create_project(
    request: Request,
    proxy: SecurityFlashProxy = Depends(get_proxy)
):
    """Proxy: Create project in SecurityFlash V1."""
    return await proxy.proxy_request(request, "/api/v1/projects")


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    request: Request,
    proxy: SecurityFlashProxy = Depends(get_proxy)
):
    """Proxy: Get project details from SecurityFlash V1."""
    return await proxy.proxy_request(request, f"/api/v1/projects/{project_id}")


@router.put("/{project_id}")
async def update_project(
    project_id: str,
    request: Request,
    proxy: SecurityFlashProxy = Depends(get_proxy)
):
    """Proxy: Update project in SecurityFlash V1."""
    return await proxy.proxy_request(request, f"/api/v1/projects/{project_id}")


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    request: Request,
    proxy: SecurityFlashProxy = Depends(get_proxy)
):
    """Proxy: Delete project in SecurityFlash V1."""
    return await proxy.proxy_request(request, f"/api/v1/projects/{project_id}")
