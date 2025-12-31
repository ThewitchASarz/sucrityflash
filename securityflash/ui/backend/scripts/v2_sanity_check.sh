#!/bin/bash
# V2 BFF Sanity Check
# Ensures V2 is a stateless proxy with NO local database or state

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║                V2 BFF SANITY CHECK (Stateless Proxy)             ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

FAILED=0

# Check 1: No alembic/ in V2 backend
echo "[1/10] Checking for alembic/ (must be in legacy)..."
if [ -d "alembic" ]; then
    echo "❌ FAIL: alembic/ exists (must be moved to docs/legacy/)"
    FAILED=1
else
    echo "✅ PASS: No alembic/ directory"
fi
echo ""

# Check 2: No models/ in V2 backend
echo "[2/10] Checking for models/ (must be in legacy)..."
if [ -d "models" ]; then
    echo "❌ FAIL: models/ exists (must be moved to docs/legacy/)"
    FAILED=1
else
    echo "✅ PASS: No models/ directory"
fi
echo ""

# Check 3: No database.py in V2 backend
echo "[3/10] Checking for database.py (must be in legacy)..."
if [ -f "database.py" ]; then
    echo "❌ FAIL: database.py exists (must be moved to docs/legacy/)"
    FAILED=1
else
    echo "✅ PASS: No database.py file"
fi
echo ""

# Check 4: No SQLAlchemy imports in main.py
echo "[4/10] Checking main.py for SQLAlchemy imports..."
if grep -i "sqlalchemy\|from database import" main.py 2>/dev/null; then
    echo "❌ FAIL: main.py imports SQLAlchemy or database"
    FAILED=1
else
    echo "✅ PASS: main.py has no SQLAlchemy imports"
fi
echo ""

# Check 5: Proxy utility exists
echo "[5/10] Checking for proxy utility..."
if [ ! -f "api/proxy.py" ]; then
    echo "❌ FAIL: api/proxy.py missing"
    FAILED=1
else
    if grep -q "SecurityFlashProxy" api/proxy.py; then
        echo "✅ PASS: Proxy utility exists"
    else
        echo "❌ FAIL: Proxy utility incomplete"
        FAILED=1
    fi
fi
echo ""

# Check 6: Routers use proxy pattern
echo "[6/10] Checking routers use proxy..."
PROXY_COUNT=$(grep -l "from api.proxy import" api/*.py 2>/dev/null | wc -l)
if [ "$PROXY_COUNT" -lt 5 ]; then
    echo "❌ FAIL: Only $PROXY_COUNT routers use proxy (need at least 5)"
    FAILED=1
else
    echo "✅ PASS: $PROXY_COUNT routers use proxy pattern"
fi
echo ""

# Check 7: No subprocess usage
echo "[7/10] Checking for subprocess usage..."
if grep -r "import subprocess\|subprocess.run" --include="*.py" . --exclude-dir=tests --exclude-dir=docs 2>/dev/null | grep -v "# no subprocess" | grep -q .; then
    echo "❌ FAIL: Found subprocess usage (V2 must not execute tools)"
    FAILED=1
else
    echo "✅ PASS: No subprocess usage"
fi
echo ""

# Check 8: SECURITYFLASH_API_URL documented
echo "[8/10] Checking SECURITYFLASH_API_URL documentation..."
if grep -q "SECURITYFLASH_API_URL" config.py 2>/dev/null; then
    echo "✅ PASS: SECURITYFLASH_API_URL is in config"
else
    echo "❌ FAIL: SECURITYFLASH_API_URL not in config"
    FAILED=1
fi
echo ""

# Check 9: Legacy directory exists with warning
echo "[9/10] Checking legacy directory..."
if [ ! -d "docs/legacy" ]; then
    echo "❌ FAIL: docs/legacy/ missing"
    FAILED=1
elif [ ! -f "docs/legacy/README.md" ]; then
    echo "❌ FAIL: docs/legacy/README.md missing"
    FAILED=1
elif grep -q "DO NOT USE" docs/legacy/README.md; then
    echo "✅ PASS: Legacy directory exists with warning"
else
    echo "❌ FAIL: Legacy README missing warning"
    FAILED=1
fi
echo ""

# Check 10: No audit log services in active code
echo "[10/10] Checking for local audit services..."
if [ -f "services/audit_log_service.py" ] || [ -f "services/audit_service.py" ]; then
    echo "❌ FAIL: Audit services exist (must be in legacy/)"
    FAILED=1
else
    echo "✅ PASS: No local audit services"
fi
echo ""

# Summary
echo "═══════════════════════════════════════════════════════════════════"
if [ $FAILED -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED"
    echo "V2 is a stateless BFF proxy (no database, no local state)"
    echo "═══════════════════════════════════════════════════════════════════"
    exit 0
else
    echo "❌ SOME CHECKS FAILED"
    echo "Fix issues above - V2 must be stateless"
    echo "═══════════════════════════════════════════════════════════════════"
    exit 1
fi
