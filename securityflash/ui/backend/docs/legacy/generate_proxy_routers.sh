#!/bin/bash
# Generate proxy routers for all V2 API endpoints

# Auth router
cat > api/auth.py << 'EOF'
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
EOF

# Scopes router
cat > api/scopes.py << 'EOF'
"""
Scopes API - BFF Proxy to SecurityFlash V1
"""
from fastapi import APIRouter, Request, Depends
from api.proxy import get_proxy, SecurityFlashProxy

router = APIRouter()

@router.get("")
async def list_scopes(request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, "/api/v1/scopes")

@router.post("")
async def create_scope(request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, "/api/v1/scopes")

@router.get("/{scope_id}")
async def get_scope(scope_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/scopes/{scope_id}")
EOF

# Runs router
cat > api/runs.py << 'EOF'
"""
Runs API - BFF Proxy to SecurityFlash V1
"""
from fastapi import APIRouter, Request, Depends
from api.proxy import get_proxy, SecurityFlashProxy

router = APIRouter()

@router.get("")
async def list_runs(request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, "/api/v1/runs")

@router.post("")
async def create_run(request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, "/api/v1/runs")

@router.get("/{run_id}")
async def get_run(run_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/runs/{run_id}")
EOF

# Approvals router
cat > api/approvals.py << 'EOF'
"""
Approvals API - BFF Proxy to SecurityFlash V1
"""
from fastapi import APIRouter, Request, Depends
from api.proxy import get_proxy, SecurityFlashProxy

router = APIRouter()

@router.get("")
async def list_approvals(request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, "/api/v1/approvals")

@router.post("/{approval_id}/approve")
async def approve_action(approval_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/approvals/{approval_id}/approve")

@router.post("/{approval_id}/reject")
async def reject_action(approval_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/approvals/{approval_id}/reject")
EOF

# Evidence router
cat > api/evidence.py << 'EOF'
"""
Evidence API - BFF Proxy to SecurityFlash V1
"""
from fastapi import APIRouter, Request, Depends
from api.proxy import get_proxy, SecurityFlashProxy

router = APIRouter()

@router.get("")
async def list_evidence(request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, "/api/v1/evidence")

@router.get("/{evidence_id}")
async def get_evidence(evidence_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    return await proxy.proxy_request(request, f"/api/v1/evidence/{evidence_id}")

@router.delete("/{evidence_id}")
async def delete_evidence(evidence_id: str, request: Request, proxy: SecurityFlashProxy = Depends(get_proxy)):
    """Proxy DELETE - V1 will return 403 (evidence is immutable)."""
    return await proxy.proxy_request(request, f"/api/v1/evidence/{evidence_id}")
EOF

# Findings router
cat > api/findings.py << 'EOF'
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
EOF

# Test Plans router
cat > api/test_plans.py << 'EOF'
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
EOF

# Reports router
cat > api/reports.py << 'EOF'
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
EOF

# Audit router
cat > api/audit.py << 'EOF'
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
EOF

echo "✓ Generated all proxy routers"
