# SecurityFlash V1 Quick Start Guide

## 🚀 Get Started in 10 Minutes

This guide walks through running the complete SecurityFlash V1 system end-to-end.

---

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Poetry (Python package manager)
- PostgreSQL client tools (optional, for debugging)

---

## Step 1: Setup Environment

```bash
# Clone/navigate to project
cd securityflash

# Copy environment template
cp .env.example .env

# Install dependencies
make install
# OR: poetry install

# Start infrastructure (Postgres, Redis, MinIO)
make docker-up

# Verify services are running
docker ps
# Should see: securityflash-postgres, securityflash-redis, securityflash-minio
```

---

## Step 2: Initialize Database

```bash
# Run Alembic migrations
make migrate
# OR: alembic upgrade head

# Verify tables created
docker exec -it securityflash-postgres psql -U xbow -d xbow -c "\dt"
# Should see: projects, scopes, runs, action_specs, approvals, evidence, audit_log
```

---

## Step 3: Start Control Plane

**Terminal 1:**
```bash
make api
# OR: python -m uvicorn apps.api.main:app --reload

# Verify API is running
curl http://localhost:8000/health
# Should return: {"status":"healthy","service":"control-plane"}
```

The Control Plane is now running on `http://localhost:8000`

---

## Step 4: Create Project, Scope, and Run

**Terminal 2 (or use Postman):**

```bash
# 1. Create Project
PROJECT_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Quick Start Test",
    "customer_id": "test-customer",
    "start_date": "2025-12-26T00:00:00Z",
    "end_date": "2026-01-26T00:00:00Z",
    "rules_of_engagement": "Test engagement for V1 quick start",
    "created_by": "admin"
  }')

PROJECT_ID=$(echo $PROJECT_RESPONSE | jq -r '.id')
echo "✅ Project created: $PROJECT_ID"

# 2. Create Scope
SCOPE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/projects/$PROJECT_ID/scopes \
  -H "Content-Type: application/json" \
  -d '{
    "scope_type": "network",
    "targets": [
      {"type": "domain", "value": "example.com", "criticality": "MEDIUM"},
      {"type": "domain", "value": "scanme.nmap.org", "criticality": "LOW"}
    ],
    "excluded_targets": [],
    "attack_vectors_allowed": ["reconnaissance", "enumeration"],
    "attack_vectors_prohibited": ["denial_of_service"],
    "approved_tools": ["nmap", "httpx"],
    "time_restrictions": {
      "start_time": "00:00 UTC",
      "end_time": "23:59 UTC",
      "blackout_dates": []
    }
  }')

SCOPE_ID=$(echo $SCOPE_RESPONSE | jq -r '.id')
echo "✅ Scope created: $SCOPE_ID"

# 3. Lock Scope (REQUIRED before starting run)
curl -s -X POST http://localhost:8000/api/v1/projects/$PROJECT_ID/scopes/$SCOPE_ID/lock \
  -H "Content-Type: application/json" \
  -d '{
    "locked_by": "admin",
    "signature": "admin-signature-quickstart"
  }'
echo "✅ Scope locked"

# 4. Create Run (status=CREATED)
RUN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/projects/$PROJECT_ID/runs \
  -H "Content-Type: application/json" \
  -d '{
    "scope_id": "'$SCOPE_ID'",
    "policy_version": "1.0.0",
    "max_iterations": 10,
    "created_by": "admin"
  }')

RUN_ID=$(echo $RUN_RESPONSE | jq -r '.id')
echo "✅ Run created: $RUN_ID (status=CREATED)"

# 5. Start Run (MUST-FIX A: CREATED → RUNNING)
curl -s -X POST http://localhost:8000/api/v1/runs/$RUN_ID/start \
  -H "Content-Type: application/json"
echo "✅ Run started (status=RUNNING)"

# Save RUN_ID for later steps
echo $RUN_ID > /tmp/securityflash_run_id.txt
echo ""
echo "🎯 Run ID: $RUN_ID"
echo "   Copy this ID for the next steps!"
```

---

## Step 5: Start Worker Runtime

**Terminal 3:**
```bash
make worker
# OR: python -m apps.workers.runner

# Worker will poll for APPROVED actions every 5 seconds
# Look for: "SecurityFlash Worker Runtime starting..."
```

---

## Step 6: Start Agent Runtime

**Terminal 4:**
```bash
# Use the RUN_ID from Step 4
RUN_ID=$(cat /tmp/securityflash_run_id.txt)

make agent RUN_ID=$RUN_ID
# OR: python -m apps.agents.runner $RUN_ID

# Agent will:
# 1. Check run.status (must be RUNNING)
# 2. Load scope and targets
# 3. Propose nmap scan for each target
# 4. Wait for approval and evidence

# Look for:
# "Run status: RUNNING. Beginning agent execution."
# "Processing target: example.com"
# "Action proposed: ... (status=PENDING_APPROVAL, risk=0.35, tier=B)"
```

---

## Step 7: Approve Actions (Reviewer Interface)

**Terminal 5 (or Terminal 2):**
```bash
RUN_ID=$(cat /tmp/securityflash_run_id.txt)

# View pending approvals
make reviewer-queue RUN_ID=$RUN_ID
# OR: python scripts/reviewer_queue.py queue --run-id $RUN_ID

# You should see a table with:
# - Action ID
# - Tool (nmap)
# - Target (example.com)
# - Risk score
# - Approval tier

# Copy the ACTION_ID from the table, then approve:
ACTION_ID="<paste-action-id-here>"

make reviewer-approve RUN_ID=$RUN_ID ACTION_ID=$ACTION_ID
# OR: python scripts/reviewer_queue.py approve --action-id $ACTION_ID --run-id $RUN_ID

# You should see:
# "✅ Action abc123... APPROVED"
# "Token issued: eyJhbGciOiJIUzI1NiI..."
# "Worker can now execute"
```

---

## Step 8: Observe Execution

Watch the terminals:

**Terminal 3 (Worker):**
```
Found 1 approved actions
Executing action abc123... (tool=nmap, target=example.com)
Token verification: PASSED
Tool execution completed: EXECUTED
Evidence created: def456...
Action abc123... → EXECUTED
```

**Terminal 4 (Agent):**
```
Waiting for evidence...
Evidence received: def456
Tool output: 1234 bytes
Processing target: scanme.nmap.org
...
```

---

## Step 9: Verify Results

**Check Evidence:**
```bash
RUN_ID=$(cat /tmp/securityflash_run_id.txt)

# List all evidence
curl -s http://localhost:8000/api/v1/runs/$RUN_ID/evidence | jq

# Should show evidence records with:
# - artifact_uri (S3 path)
# - artifact_hash (SHA256)
# - generated_by: "worker"
# - metadata (tool output)
```

**Check Audit Log:**
```bash
# Query database
docker exec -it securityflash-postgres psql -U xbow -d xbow -c \
  "SELECT event_type, actor, created_at FROM audit_log WHERE run_id='$RUN_ID' ORDER BY created_at;"

# Should show:
# RUN_CREATED
# SCOPE_LOCKED
# RUN_STARTED
# ACTION_PROPOSED
# ACTION_APPROVED
# ACTION_EXECUTED
# EVIDENCE_STORED
```

**Check Run Status:**
```bash
curl -s http://localhost:8000/api/v1/runs/$RUN_ID | jq

# Should show:
# - status: "RUNNING" or "COMPLETED"
# - iteration_count: number of iterations
# - All action_specs with statuses
```

---

## Step 10: Verify Immutability

**Try to Delete Evidence (Should Fail):**
```bash
EVIDENCE_ID=$(curl -s http://localhost:8000/api/v1/runs/$RUN_ID/evidence | jq -r '.[0].id')

curl -X DELETE http://localhost:8000/api/v1/runs/$RUN_ID/evidence/$EVIDENCE_ID

# Should return:
# {"detail":"Evidence cannot be deleted. Evidence is immutable..."}
# Status: 403 Forbidden
```

**Verify FSM Protection:**
```bash
# Try invalid state transition (not possible via API, would require direct DB)
# FSM is enforced in all routers
```

---

## 🎉 Success!

You've successfully run the complete SecurityFlash V1 workflow:

✅ Control Plane governs all actions
✅ Agent proposes ActionSpecs
✅ Policy Engine evaluates (scope, tool, risk)
✅ Human reviewer approves
✅ Worker executes with token verification
✅ Evidence stored immutably
✅ Audit trail recorded
✅ All MUST-FIX items enforced

---

## Troubleshooting

**"Run must be in RUNNING state"**
- Make sure you ran Step 4.5: `POST /runs/{run_id}/start`
- Check run status: `curl http://localhost:8000/api/v1/runs/$RUN_ID`

**"No pending approvals"**
- Agent may have finished already
- Check action_specs: `curl http://localhost:8000/api/v1/runs/$RUN_ID/action-specs`

**"Token verification failed"**
- Check POLICY_SIGNING_SECRET in .env matches between API and Worker
- Ensure clock is synchronized (JWT expiry check)

**"Tool not found"**
- Worker needs nmap/httpx installed: `sudo apt install nmap httpx` (or via brew on Mac)
- Or mock the tools for testing

**Database connection error**
- Verify Postgres is running: `docker ps | grep postgres`
- Check DATABASE_URL in .env

---

## Next Steps

**Production Deployment:**
- Configure real RBAC (replace "system" user)
- Set up proper secrets management
- Add HTTPS/TLS
- Configure MinIO bucket policy (see `infra/minio/minio_policy.json`)
- Set up monitoring and alerting

**Extend Functionality:**
- Add more agent types (see `apps/agents/orchestrator.py:SimpleHttpAgent`)
- Implement LLM-based reasoning (use `agent.query_llm()`)
- Add custom tools (extend worker tool wrappers)
- Build Web UI (integrate with approval endpoints)

**Testing:**
- Write unit tests for Policy Engine
- Write unit tests for Status FSM
- Write E2E acceptance tests
- Load testing

---

## Clean Up

```bash
# Stop all services
make docker-down
# OR: docker-compose down

# Clean Python cache
make clean

# Remove database data (if needed)
docker volume rm securityflash_postgres-data securityflash_minio-data
```

---

**Questions?** Check `README.md` or `IMPLEMENTATION_STATUS.md`
