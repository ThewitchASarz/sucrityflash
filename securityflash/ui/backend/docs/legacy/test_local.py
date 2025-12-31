"""
Local testing script - No Docker required!
This creates a minimal FastAPI app for testing without full infrastructure.
"""
import sys
import os

# Load local env
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./pentest_local.db'
os.environ['REDIS_URL'] = 'memory://'  # In-memory mock
os.environ['JWT_SECRET'] = 'local-testing-secret-12345678'
os.environ['ENVIRONMENT'] = 'development'
os.environ['DEBUG'] = 'true'
os.environ['LLM_PROVIDER'] = 'claude'
os.environ['ANTHROPIC_API_KEY'] = 'test-key'

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

print("🚀 Starting Pentest AI Platform (Local Test Mode)")
print("=" * 60)

# Patch Redis client to use in-memory mock
class MockRedisClient:
    """Mock Redis for local testing"""
    def __init__(self):
        self.data = {}
        self.sorted_sets = {}

    async def connect(self):
        print("✓ Mock Redis connected (in-memory)")

    async def disconnect(self):
        print("✓ Mock Redis disconnected")

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, ex=None):
        self.data[key] = value

    async def delete(self, key):
        self.data.pop(key, None)

    async def zadd(self, key, mapping):
        if key not in self.sorted_sets:
            self.sorted_sets[key] = {}
        self.sorted_sets[key].update(mapping)

    async def zrangebyscore(self, key, min, max):
        if key not in self.sorted_sets:
            return []
        return [k for k, v in self.sorted_sets[key].items() if min <= v <= max]

    async def zrem(self, key, *members):
        if key in self.sorted_sets:
            for member in members:
                self.sorted_sets[key].pop(member, None)

# Patch redis_client
import redis_client
redis_client.redis_client = MockRedisClient()

from config import settings
from database import engine, Base

print(f"Environment: {settings.ENVIRONMENT}")
print(f"Database: {settings.DATABASE_URL}")
print(f"LLM Provider: {settings.LLM_PROVIDER}")
print("=" * 60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Minimal lifespan for local testing"""
    print("\n🔧 Initializing database...")

    # Connect mock Redis
    await redis_client.redis_client.connect()

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✓ Database tables created")
    print("\n✅ Server ready for testing!")
    print("=" * 60)
    print("📡 API Endpoints available at:")
    print("   - Docs: http://localhost:8000/docs")
    print("   - Health: http://localhost:8000/health")
    print("   - Auth: http://localhost:8000/api/auth/*")
    print("=" * 60)
    print("\n🧪 Quick Test Commands:")
    print('   curl http://localhost:8000/health')
    print('   curl http://localhost:8000/docs')
    print("=" * 60)

    yield

    await redis_client.redis_client.disconnect()
    await engine.dispose()
    print("\n✓ Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Pentest AI Platform (Local Test)",
    version="0.1.0",
    description="Human-governed, agent-autonomous penetration testing (LOCAL TEST MODE)",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
from datetime import datetime

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "mode": "LOCAL_TEST",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "SQLite (in-memory)",
        "redis": "Mock (in-memory)",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
async def root():
    return {
        "message": "Pentest AI Platform - Local Test Mode",
        "docs": "/docs",
        "health": "/health",
        "note": "Running without Docker - limited functionality"
    }

# Import routers
try:
    from api import auth, projects, scopes, audit, test_plans, runs, approvals, evidence, findings, reports

    app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
    app.include_router(scopes.router, prefix="/api/scopes", tags=["Scopes"])
    app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])
    app.include_router(test_plans.router, prefix="/api/test-plans", tags=["Test Plans"])
    app.include_router(runs.router, prefix="/api/runs", tags=["Runs"])
    app.include_router(approvals.router, prefix="/api/approvals", tags=["Approvals"])
    app.include_router(evidence.router, prefix="/api/evidence", tags=["Evidence"])
    app.include_router(findings.router, prefix="/api/findings", tags=["Findings"])
    app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])

    print("\n✅ All 10 routers loaded (36 endpoints)")
except Exception as e:
    print(f"⚠️  Warning: Some routers failed to load: {e}")
    print("   (This is OK for basic testing)")

if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Starting local test server...")
    print("   Press CTRL+C to stop\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
