# SecurityFlash - AI-Powered Penetration Testing Platform

**Production-grade autonomous penetration testing with human-in-the-loop governance**

## 🔥 Features

- **AI Agent-Driven**: Autonomous agents propose and execute security tests
- **Human-in-the-Loop**: Policy engine with approval workflow for high-risk actions
- **Immutable Evidence**: Cryptographically verified audit trail stored in S3/MinIO
- **Real-time Monitoring**: Live dashboard showing agent activity and pending approvals
- **Policy Governance**: Risk scoring, approval tiers, and rate limiting
- **Full Audit Trail**: Every action logged with timestamps and actor attribution

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│  React UI   │─────▶│   V2 BFF     │─────▶│  SecurityFlash  │
│  (Port 3000)│      │  (Port 3001) │      │   V1 API        │
│             │      │  Stateless   │      │  (Port 8000)    │
└─────────────┘      │   Proxy      │      │                 │
                     └──────────────┘      │  ┌───────────┐  │
                                           │  │PostgreSQL │  │
                     ┌──────────────┐      │  │  Redis    │  │
                     │    Agent     │─────▶│  │  MinIO    │  │
                     │   Runtime    │      │  └───────────┘  │
                     └──────────────┘      └─────────────────┘
                     
                     ┌──────────────┐              │
                     │   Worker     │──────────────┘
                     │   Runtime    │   Executes approved
                     └──────────────┘   actions
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Docker & Docker Compose
- PostgreSQL, Redis, MinIO (or use Docker)

### 1. Clone Repository
```bash
git clone https://github.com/ThewitchASarz/sucrityflash.git
cd sucrityflash
```

### 2. Start Infrastructure (Docker)
```bash
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- MinIO (ports 9000, 9001)

### 3. Setup V1 API (SecurityFlash)
```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python init_db.py

# Start V1 API
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

### 4. Start Agent & Worker
```bash
# In separate terminals:

# Worker (executes approved actions)
python -m apps.workers.runner

# Agent (proposes actions for a run)
python -m apps.agents.runner <run_id>
```

### 5. Setup V2 BFF (Optional - for UI)
```bash
cd ../pentest-ai-platform/backend
export SECURITYFLASH_API_URL=http://localhost:8000
python main.py  # Runs on port 3001
```

### 6. Setup React UI (Optional)
```bash
cd ../frontend
npm install
npm start  # Runs on port 3000
```

## 📊 Using the Platform

### Via API

1. **Create Project**
```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Security Assessment",
    "customer_id": "customer-123",
    "description": "Q4 2024 pentest"
  }'
```

2. **Create Scope**
```bash
curl -X POST http://localhost:8000/api/v1/projects/{project_id}/scopes \
  -H "Content-Type: application/json" \
  -d '{
    "scope_json": {
      "targets": [{"type": "domain", "value": "example.com", "criticality": "HIGH"}],
      "scope_type": "web_app",
      "approved_tools": ["nmap", "httpx"]
    }
  }'
```

3. **Lock Scope**
```bash
curl -X POST http://localhost:8000/api/v1/projects/{project_id}/scopes/{scope_id}/lock \
  -H "Content-Type: application/json" \
  -d '{
    "locked_by": "security-lead",
    "signature": "digital-signature-here"
  }'
```

4. **Create & Start Run**
```bash
# Create run
curl -X POST http://localhost:8000/api/v1/projects/{project_id}/runs \
  -H "Content-Type: application/json" \
  -d '{
    "scope_id": "{scope_id}",
    "policy_version": "1.0.0",
    "created_by": "security-lead"
  }'

# Start run (explicit state transition)
curl -X POST http://localhost:8000/api/v1/runs/{run_id}/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

5. **Monitor Pending Approvals**
```bash
curl http://localhost:8000/api/v1/runs/{run_id}/approvals/pending
```

6. **Approve Action**
```bash
curl -X POST http://localhost:8000/api/v1/runs/{run_id}/approvals/{action_id}/approve \
  -H "Content-Type: application/json" \
  -d '{
    "approved_by": "security-lead",
    "signature": "approval-signature"
  }'
```

### Via UI (http://localhost:3000)

1. Open browser to `http://localhost:3000`
2. Click "New Project" to create a project
3. Add scope with targets
4. Click "Start Pentest"
5. **Monitor pending approvals** in yellow-highlighted section
6. Click "✅ APPROVE" button to approve actions
7. Watch timeline and evidence collection in real-time

## 🛠️ Monitoring Tools

### Quick Status Check
```bash
python check_status.py
```

### Approve Action (CLI)
```bash
python approve.py <run_id> <action_id>
```

### Live Monitor Dashboard
```bash
python monitor.py  # Auto-refreshes every 5 seconds
```

## 📁 Project Structure

```
securityflash/
├── apps/
│   ├── api/              # V1 API (FastAPI)
│   │   ├── routers/      # API endpoints
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # Business logic
│   ├── agents/           # Agent runtime
│   │   ├── orchestrator.py
│   │   └── base.py
│   └── workers/          # Worker runtime
│       ├── runner.py
│       └── tools/        # Tool executors
├── docker-compose.yml    # Infrastructure
├── init_db.py           # Database initialization
├── requirements.txt
├── check_status.py      # Monitoring script
├── approve.py           # CLI approval tool
└── monitor.py           # Live dashboard

pentest-ai-platform/
├── backend/             # V2 BFF (Stateless proxy)
└── frontend/            # React UI
```

## 🔒 Security Features

1. **Policy Engine**: All actions evaluated before execution
2. **Approval Workflow**: High-risk actions require human approval
3. **JWT Token Verification**: Workers verify approval tokens
4. **Immutable Evidence**: Evidence cannot be deleted or modified
5. **Audit Logging**: Complete audit trail with timestamps
6. **Scope Locking**: Scopes are immutable once pentest starts
7. **Rate Limiting**: Prevents runaway automation

## 📊 Production Test Results

Successfully ran production pentest with:
- ✅ 90+ evidence records collected
- ✅ 94 audit log entries
- ✅ Real nmap scans executed
- ✅ Approval workflow functional
- ✅ Immutable evidence storage verified

## 🤝 Contributing

This is a production security tool. Please follow secure development practices:
- No hardcoded credentials
- All security actions require approval
- Maintain audit trail integrity
- Test thoroughly before deploying

## 📄 License

[Add your license here]

## 🙏 Credits

Built with Claude Code for secure, governed penetration testing.

## 🎨 UI Components (Optional)

The `ui/` directory contains:
- **backend/** - V2 BFF (Stateless proxy to V1)
- **frontend/** - React monitoring dashboard

### Setup UI
```bash
# V2 BFF
cd ui/backend
export SECURITYFLASH_API_URL=http://localhost:8000
python main.py  # Port 3001

# React UI
cd ui/frontend
npm install
npm start  # Port 3000
```

Access the monitoring dashboard at `http://localhost:3000`
