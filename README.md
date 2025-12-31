# SecurityFlash - Complete AI Penetration Testing Platform

**Enterprise-grade autonomous penetration testing with human-in-the-loop governance**

This repository contains the complete SecurityFlash platform including:
- **SecurityFlash V1 API** - Core governance and policy engine
- **Agent & Worker Runtime** - Autonomous execution framework
- **V2 BFF** - Stateless proxy for frontend
- **React Monitoring UI** - Real-time dashboard with approval workflow

## 🎯 Production Test Results

Successfully executed production pentest with:
- ✅ **90+ evidence records** collected from real nmap scans
- ✅ **94 audit log entries** tracking all activity
- ✅ **Human-in-the-loop approval** workflow tested and functional
- ✅ **Immutable evidence storage** with cryptographic verification
- ✅ **Real-time monitoring** dashboard operational

## 📁 Repository Structure

```
PyCharmMiscProject/
├── securityflash/           # V1 API (Core Platform)
│   ├── apps/
│   │   ├── api/            # FastAPI application
│   │   ├── agents/         # Agent runtime
│   │   └── workers/        # Worker runtime
│   ├── docker-compose.yml  # Infrastructure (PostgreSQL, Redis, MinIO)
│   ├── init_db.py         # Database initialization
│   ├── check_status.py    # Quick status monitoring
│   ├── approve.py         # CLI approval tool
│   └── monitor.py         # Live dashboard

├── pentest-ai-platform/    # UI Components
│   ├── backend/           # V2 BFF (Proxy)
│   └── frontend/          # React monitoring dashboard

└── [Test scripts and utilities]
```

## 🚀 Quick Start

### 1. Start Infrastructure
```bash
cd securityflash
docker-compose up -d
```

### 2. Initialize Database
```bash
cp .env.example .env
# Edit .env with your credentials
python init_db.py
```

### 3. Start V1 API
```bash
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

### 4. Start Worker & Agent
```bash
# Terminal 1: Worker
python -m apps.workers.runner

# Terminal 2: Agent (for a specific run)
python -m apps.agents.runner <run_id>
```

### 5. Start UI (Optional)
```bash
# V2 BFF
cd pentest-ai-platform/backend
export SECURITYFLASH_API_URL=http://localhost:8000
python main.py  # Port 3001

# React UI
cd ../frontend
npm install
npm start  # Port 3000
```

## 🔥 Key Features

### Policy Engine
- Risk scoring algorithm
- Multi-tier approval workflow (A/B/C)
- Rate limiting per run
- Scope boundary enforcement
- Tool allowlist validation

### Agent Runtime
- Autonomous action proposal
- Checkpoint/resume capability
- LLM audit logging
- Scope-aware targeting
- Evidence-based iteration

### Worker Runtime
- JWT token verification
- Tool execution sandboxing
- Resource limits (CPU, memory, timeout)
- Immutable evidence storage
- Cryptographic hashing

### Monitoring Dashboard
- ⏳ **Pending Approvals** - One-click approval buttons
- 📊 **Live Stats** - Real-time metrics
- 🤖 **Timeline** - Complete audit trail
- 📊 **Evidence** - All collected artifacts

## 🛠️ Monitoring Tools

```bash
# Quick status check
python check_status.py

# Approve action
python approve.py <run_id> <action_id>

# Live monitoring dashboard
python monitor.py
```

## 📊 API Usage

### Create Project
```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Pentest",
    "customer_id": "customer-123"
  }'
```

### Create & Lock Scope
```bash
curl -X POST http://localhost:8000/api/v1/projects/{project_id}/scopes \
  -d '{
    "scope_json": {
      "targets": [{"type": "domain", "value": "example.com"}],
      "approved_tools": ["nmap", "httpx"]
    }
  }'

curl -X POST http://localhost:8000/api/v1/projects/{project_id}/scopes/{scope_id}/lock \
  -d '{"locked_by": "security-lead", "signature": "sig"}'
```

### Start Run
```bash
curl -X POST http://localhost:8000/api/v1/projects/{project_id}/runs \
  -d '{"scope_id": "{scope_id}", "created_by": "lead"}'

curl -X POST http://localhost:8000/api/v1/runs/{run_id}/start \
  -d '{}'
```

### Monitor & Approve
```bash
# Check pending approvals
curl http://localhost:8000/api/v1/runs/{run_id}/approvals/pending

# Approve action
curl -X POST http://localhost:8000/api/v1/runs/{run_id}/approvals/{action_id}/approve \
  -d '{"approved_by": "lead", "signature": "sig"}'

# View evidence
curl http://localhost:8000/api/v1/runs/{run_id}/evidence

# View timeline
curl http://localhost:8000/api/v1/runs/{run_id}/timeline
```

## 🔒 Security Architecture

1. **Immutable Evidence** - Cannot be deleted or modified
2. **Cryptographic Verification** - SHA256 hashing of all artifacts
3. **Scope Locking** - Prevents scope modification during execution
4. **JWT Token Verification** - Workers verify all approval tokens
5. **Audit Logging** - Complete trail of all actions
6. **Policy Enforcement** - Three-layer validation

## 📦 Dependencies

- Python 3.9+
- FastAPI
- SQLAlchemy + PostgreSQL
- Redis (for future job queuing)
- MinIO/S3 (evidence storage)
- Node.js 16+ (for UI)
- React 19+ (monitoring dashboard)

## 🚀 Cloud Deployment

Recommended infrastructure:
- **Compute**: 2-4 GB RAM per service
- **Database**: PostgreSQL (managed service)
- **Cache**: Redis (managed service)
- **Storage**: S3/GCS for evidence
- **Container**: Docker + Kubernetes

## 📝 License

Private repository - All rights reserved

## 🙏 Built With

- FastAPI for high-performance async API
- SQLAlchemy for robust ORM
- React for real-time monitoring
- MinIO for S3-compatible storage
- PostgreSQL for reliable data storage

---

**🤖 Generated with Claude Code (https://claude.com/claude-code)**

**Co-Authored-By: Claude <noreply@anthropic.com>**
