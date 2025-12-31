"""
Auth API - Pass-through to SecurityFlash V1

V2 does NOT maintain its own user table or sessions.
All auth happens in SecurityFlash V1.
"""
from fastapi import APIRouter, Request, Depends
from api.proxy import get_proxy, SecurityFlashProxy

router = APIRouter()

@router.post("/login")
async def login(request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    """Proxy: Login via SecurityFlash V1."""
    return await proxy.proxy_request(request, "/api/v1/auth/login")

@router.post("/register")
async def register(request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    """Proxy: Register via SecurityFlash V1."""
    return await proxy.proxy_request(request, "/api/v1/auth/register")

@router.get("/me")
async def get_current_user(request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    """Proxy: Get current user from SecurityFlash V1."""
    return await proxy.proxy_request(request, "/api/v1/auth/me")
