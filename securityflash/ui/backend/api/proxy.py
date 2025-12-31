"""
Generic Proxy Utility for V2 BFF

V2 is a stateless BFF that ONLY proxies requests to SecurityFlash V1.
All data, state, governance, and audit logs live in V1.
"""
import httpx
from fastapi import Request, Response, HTTPException
from typing import Optional
import os


class SecurityFlashProxy:
    """
    Proxy layer for SecurityFlash V1 API.
    
    V2 BFF is stateless - it only forwards requests to V1 and returns responses.
    No local database, no local state, no local audit logs.
    """
    
    def __init__(self):
        self.base_url = os.getenv("SECURITYFLASH_API_URL")
        if not self.base_url:
            raise ValueError("SECURITYFLASH_API_URL environment variable is required")
        
        # Remove trailing slash
        self.base_url = self.base_url.rstrip("/")
        
        self.timeout = float(os.getenv("SECURITYFLASH_TIMEOUT", "30.0"))
    
    async def proxy_request(
        self,
        request: Request,
        path: str,
        method: Optional[str] = None
    ) -> Response:
        """
        Generic proxy function.
        
        Forwards request to SecurityFlash V1 and returns response unchanged.
        
        Args:
            request: FastAPI Request object
            path: Target path in V1 (e.g., "/api/v1/projects")
            method: HTTP method override (default: use request.method)
        
        Returns:
            FastAPI Response with V1's status code, headers, and body
        """
        method = method or request.method
        url = f"{self.base_url}{path}"
        
        # Forward headers (especially Authorization)
        headers = dict(request.headers)
        # Remove host header to avoid conflicts
        headers.pop("host", None)
        
        # Get request body if present
        body = None
        if method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        # Forward query parameters
        params = dict(request.query_params)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    content=body
                )
                
                # Return V1's response unchanged
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.headers.get("content-type")
                )
        
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="SecurityFlash V1 timeout - check if V1 is running"
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Cannot connect to SecurityFlash V1 - check SECURITYFLASH_API_URL"
            )
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Error proxying to SecurityFlash V1: {str(e)}"
            )


# Singleton proxy instance
_proxy: Optional[SecurityFlashProxy] = None


def get_proxy() -> SecurityFlashProxy:
    """Get or create proxy singleton."""
    global _proxy
    if _proxy is None:
        _proxy = SecurityFlashProxy()
    return _proxy
