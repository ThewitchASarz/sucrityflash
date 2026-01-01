"""
Proxy Contract Tests

Ensures V2 BFF is a pure proxy with no local state or governance logic.
"""
import pytest
import os
from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parents[1]


def test_no_sqlalchemy_imports():
    """V2 BFF must NOT import SQLAlchemy (no database)."""
    # Check main.py
    with open(BASE_DIR / "main.py", "r") as f:
        content = f.read()
        assert "sqlalchemy" not in content.lower(), "main.py must not import SQLAlchemy"
        assert "database" not in content.lower() or "database" in "# no database", "main.py must not reference database"
    
    # Check config.py
    with open(BASE_DIR / "config.py", "r") as f:
        content = f.read()
        assert "DATABASE_URL" not in content, "config.py must not have DATABASE_URL"


def test_no_models_directory():
    """V2 BFF must NOT have models/ directory (no local models)."""
    assert not (BASE_DIR / "models").exists(), "models/ directory must not exist (moved to docs/legacy/)"


def test_no_alembic_directory():
    """V2 BFF must NOT have alembic/ directory (no migrations)."""
    assert not (BASE_DIR / "alembic").exists(), "alembic/ directory must not exist (moved to docs/legacy/)"


def test_no_database_file():
    """V2 BFF must NOT have database.py (no DB connection)."""
    assert not (BASE_DIR / "database.py").exists(), "database.py must not exist (moved to docs/legacy/)"


def test_proxy_utility_exists():
    """V2 BFF must have proxy utility."""
    proxy_path = BASE_DIR / "api" / "proxy.py"
    assert proxy_path.exists(), "api/proxy.py must exist"
    
    with open(proxy_path, "r") as f:
        content = f.read()
        assert "SecurityFlashProxy" in content, "Must have SecurityFlashProxy class"
        assert "proxy_request" in content, "Must have proxy_request method"


def test_routers_use_proxy():
    """All API routers must use proxy pattern."""
    routers = [
        BASE_DIR / "api" / "projects.py",
        BASE_DIR / "api" / "scopes.py",
        BASE_DIR / "api" / "runs.py",
        BASE_DIR / "api" / "approvals.py",
        BASE_DIR / "api" / "evidence.py",
        BASE_DIR / "api" / "findings.py"
    ]
    
    for router in routers:
        if not router.exists():
            continue
            
        with open(router, "r") as f:
            content = f.read()
            assert "from api.proxy import" in content, f"{router} must import proxy"
            assert "proxy_request" in content, f"{router} must use proxy_request"
            # Must NOT directly instantiate models or access DB
            assert "Session" not in content or "SessionLocal" not in content, f"{router} must not use database sessions"


def test_no_audit_log_service():
    """V2 BFF must NOT have local audit log service."""
    assert not (BASE_DIR / "services" / "audit_log_service.py").exists(), "audit_log_service.py must be in legacy/"
    assert not (BASE_DIR / "services" / "audit_service.py").exists(), "audit_service.py must be in legacy/"


def test_legacy_directory_exists():
    """Legacy DB files must be in docs/legacy/ with warning."""
    legacy_dir = BASE_DIR / "docs" / "legacy"
    assert legacy_dir.exists(), "docs/legacy/ must exist"
    assert (legacy_dir / "README.md").exists(), "docs/legacy/README.md must exist"
    
    with open(legacy_dir / "README.md", "r") as f:
        content = f.read()
        assert "DO NOT USE" in content, "Legacy README must warn against use"


def test_securityflash_api_url_required():
    """Config must require SECURITYFLASH_API_URL."""
    with open(BASE_DIR / "config.py", "r") as f:
        content = f.read()
        assert "SECURITYFLASH_API_URL" in content, "config.py must have SECURITYFLASH_API_URL"


def test_main_has_no_db_initialization():
    """main.py must not initialize database."""
    with open(BASE_DIR / "main.py", "r") as f:
        content = f.read()
        assert "engine.dispose" not in content, "main.py must not dispose database engine"
        assert "create_all" not in content, "main.py must not create database tables"
        assert "Base.metadata" not in content, "main.py must not reference Base.metadata"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
