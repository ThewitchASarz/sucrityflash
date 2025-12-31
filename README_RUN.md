# Running SecurityFlash Suite

**Architecture:**
- **SecurityFlash V1** = Single source of truth (governance, execution, evidence, audit)
- **V2 BFF** = Stateless proxy to V1 (no database, no state)
- **V2 Frontend** = Next.js UI

---

## Prerequisites

- Docker & Docker Compose (recommended) **OR**
- Python 3.9+, Node.js 16+, PostgreSQL, Redis, MinIO (manual setup)

---

## Option 1: Docker Compose (Recommended)

### Start Full Suite

```bash
cd /Users/annalealayton/PyCharmMiscProject

# Start all services
docker-compose up

# Or run in background
docker-compose up -d
```

**Services will start:**
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- MinIO: `localhost:9000` (console: `localhost:9001`)
- SecurityFlash V1 API: `http://localhost:8000`
- SecurityFlash V1 Worker: (background process)
- V2 BFF: `http://localhost:3001`
- V2 Frontend: `http://localhost:3000`

### Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| **V1 Control Plane** | http://localhost:8000 | SecurityFlash API |
| **V1 API Docs** | http://localhost:8000/docs | Swagger UI |
| **V2 BFF** | http://localhost:3001 | Proxy to V1 |
| **V2 Frontend** | http://localhost:3000 | Main UI |
| **MinIO Console** | http://localhost:9001 | Evidence storage |

### Stop Services

```bash
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

---

## Option 2: Manual Setup (Development)

### Step 1: Start SecurityFlash V1 Only

```bash
cd securityflash

# 1. Setup environment
cp .env.example .env
# Edit .env with your config

# 2. Install dependencies
pip install -e .

# 3. Start PostgreSQL (if not running)
# macOS: brew services start postgresql
# Linux: sudo systemctl start postgresql

# 4. Start Redis (if not running)
# macOS: brew services start redis
# Linux: sudo systemctl start redis

# 5. Run database migrations
alembic upgrade head

# 6. Start V1 Control Plane
make run-api
# Or: cd apps/api && uvicorn main:app --reload --port 8000

# 7. In another terminal, start V1 Worker Runtime
make run-worker
# Or: cd apps/workers && python worker_main.py
```

**Verify V1:**
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

---

### Step 2: Start V2 BFF (Stateless Proxy)

```bash
cd pentest-ai-platform/backend

# 1. Set environment variables
export SECURITYFLASH_API_URL=http://localhost:8000
export PORT=3001

# 2. Install dependencies (if not already installed)
pip install fastapi uvicorn httpx

# 3. Start V2 BFF
python main.py
```

**Verify V2 BFF:**
```bash
curl http://localhost:3001/health
# Expected: {"status":"healthy","v1_healthy":true}
```

---

### Step 3: Start V2 Frontend (Optional)

```bash
cd pentest-ai-platform/frontend

# 1. Set environment variables
export NEXT_PUBLIC_API_BASE_URL=http://localhost:3001/api/v1

# 2. Install dependencies
npm install

# 3. Start Next.js dev server
npm run dev
```

**Access UI:**
```
http://localhost:3000
```

---

## Environment Variables

### SecurityFlash V1 (securityflash/.env)

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/securityflash

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO (evidence storage)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Environment
ENVIRONMENT=development
DEBUG=true

# JWT
JWT_SECRET=your-secret-key-change-in-production
```

### V2 BFF (pentest-ai-platform/backend/.env)

```bash
# SecurityFlash V1 connection (REQUIRED)
SECURITYFLASH_API_URL=http://localhost:8000

# BFF server
PORT=3001
ENVIRONMENT=development
```

### V2 Frontend (pentest-ai-platform/frontend/.env.local)

```bash
# V2 BFF connection
NEXT_PUBLIC_API_BASE_URL=http://localhost:3001/api/v1
```

---

## Verification

### 1. Check V1 is Running

```bash
# Health check
curl http://localhost:8000/health

# API docs
open http://localhost:8000/docs
```

### 2. Check V2 BFF is Proxying

```bash
# Health check (should show V1 health)
curl http://localhost:3001/health

# Test proxy (login)
curl -X POST http://localhost:3001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"admin"}'
```

### 3. Check Frontend

```bash
open http://localhost:3000
```

---

## Running Tests

### V2 BFF Contract Tests

```bash
cd pentest-ai-platform/backend

# Run proxy contract tests
pytest tests/test_proxy_contract.py -v

# Expected: All tests pass (V2 is stateless)
```

### V2 Sanity Check

```bash
cd pentest-ai-platform/backend

# Run sanity check
bash scripts/v2_sanity_check.sh

# Expected: ALL CHECKS PASSED (10/10)
```

### Repo-Wide Sanity Check

```bash
cd /Users/annalealayton/PyCharmMiscProject

# Run repo sanity check
bash scripts/repo_sanity_check.sh

# Expected: ALL CHECKS PASSED (8/8)
```

---

## Troubleshooting

### V1 Not Responding

**Symptom:** V2 BFF shows `v1_healthy: false`

**Fix:**
```bash
# Check V1 is running
curl http://localhost:8000/health

# If not, start V1
cd securityflash && make run-api
```

### V2 BFF Proxy Errors

**Symptom:** V2 returns 502/503 errors

**Fix:**
```bash
# Check SECURITYFLASH_API_URL is set
echo $SECURITYFLASH_API_URL

# If not set
export SECURITYFLASH_API_URL=http://localhost:8000

# Restart V2 BFF
cd pentest-ai-platform/backend && python main.py
```

### Database Connection Errors

**Symptom:** V1 fails to start with database errors

**Fix:**
```bash
# Check PostgreSQL is running
psql -U postgres -c "SELECT 1"

# Create database if missing
createdb -U postgres securityflash

# Run migrations
cd securityflash && alembic upgrade head
```

### Redis Connection Errors

**Symptom:** V1 fails to connect to Redis

**Fix:**
```bash
# Check Redis is running
redis-cli ping

# If not running
# macOS: brew services start redis
# Linux: sudo systemctl start redis
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT (Browser)                            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              V2 Frontend (Next.js) :3000                        │
│              - UI only, no business logic                       │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              V2 BFF (FastAPI) :3001                             │
│              - Stateless proxy                                  │
│              - NO database                                      │
│              - NO governance logic                              │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│          SecurityFlash V1 (Control Plane) :8000                 │
│          - Single source of truth                               │
│          - Governance, policy, approvals                        │
│          - Evidence storage (immutable)                         │
│          - Audit logs                                           │
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐      │
│  │  PostgreSQL  │   │    Redis     │   │    MinIO     │      │
│  │  (Projects,  │   │  (Events,    │   │  (Evidence   │      │
│  │   Scopes,    │   │   Streams)   │   │   Storage)   │      │
│  │   Evidence)  │   │              │   │              │      │
│  └──────────────┘   └──────────────┘   └──────────────┘      │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │            Worker Runtime                                 │ │
│  │            - Executes tools (nmap, httpx, etc.)          │ │
│  │            - Stores evidence                             │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Principles

1. **SecurityFlash V1 is the authority**
   - All data lives in V1
   - All governance happens in V1
   - All tool execution happens in V1

2. **V2 BFF is stateless**
   - No database
   - No local state
   - Pure HTTP proxy

3. **V2 Frontend is presentation only**
   - Calls V2 BFF
   - BFF proxies to V1
   - No direct V1 access

---

## Quick Commands Reference

```bash
# Start full suite (Docker)
docker-compose up

# Start V1 only
cd securityflash && make run-api

# Start V2 BFF
cd pentest-ai-platform/backend
export SECURITYFLASH_API_URL=http://localhost:8000
python main.py

# Start V2 Frontend
cd pentest-ai-platform/frontend
npm run dev

# Verify V2 is stateless
cd pentest-ai-platform/backend
bash scripts/v2_sanity_check.sh

# Run contract tests
pytest tests/test_proxy_contract.py -v
```

---

**Status:** V2 is now a stateless BFF proxy  
**Architecture:** Single source of truth = SecurityFlash V1  
**Ready for:** Development, Testing, Production
