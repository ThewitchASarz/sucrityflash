# SecurityFlash Architecture Cleanup Summary

## Completed Tasks

### A) ✅ Clean V2 Backend Surface Area

**Goal**: Remove all non-proxy code from V2 BFF to maintain architectural purity.

**Changes**:
- Moved the following directories to `pentest-ai-platform/backend/docs/legacy/`:
  - `agents/` - Agent runtime (belongs in V1 only)
  - `workers/` - Worker runtime (belongs in V1 only)
  - `tools/` - Tool implementations (belongs in V1 only)
  - `tools_experimental/` - Experimental tools (belongs in V1 only)
  - `services/` - Business logic services (belongs in V1 only)
  - `alembic.ini` - Database migrations (V2 is stateless)
  - `init_db.py` - Database initialization (V2 has no DB)
  - `redis_client.py` - Redis client (V2 is stateless)

**Result**: V2 BFF now contains ONLY:
- `main.py` - FastAPI app with lifespan and CORS
- `api/` - Proxy route definitions
- `clients/` - V1 API client
- `api/proxy.py` - Generic proxy utility
- `config.py` - Configuration
- `tests/` - Tests

---

### B) ✅ Fix V1 Scopes API to Match UI Needs

**Goal**: Add missing CRUD endpoints for scopes with proper lock enforcement.

**Changes to** `securityflash/apps/api/routers/scopes.py`:

1. **Added GET list endpoint**:
   ```python
   @router.get("", response_model=list[ScopeResponse])
   def list_scopes(project_id: str, db: Session = Depends(get_db))
   ```
   - Returns all scopes for a project
   - Ordered by `created_at` descending

2. **Added PUT update endpoint**:
   ```python
   @router.put("/{scope_id}", response_model=ScopeResponse)
   def update_scope(...)
   ```
   - Updates scope_json
   - Returns 409 Conflict if scope is locked
   - Increments version on update
   - Logs to audit trail

3. **Added DELETE endpoint**:
   ```python
   @router.delete("/{scope_id}", status_code=204)
   def delete_scope(...)
   ```
   - Returns 409 Conflict if scope is locked
   - Logs to audit trail before deletion
   - Enforces immutability guarantee

**Lock Enforcement**:
- Both PUT and DELETE check `scope.locked_at`
- If locked, return HTTP 409 with message: "Cannot [update/delete] locked scope. Locked scopes are immutable to ensure run integrity."

---

### C) ✅ Verify RunCreate Requires scope_id

**Goal**: Ensure run creation validates scope_id and enforces locked scope requirement.

**Status**: Already implemented correctly in `securityflash/apps/api/schemas/run.py`:
```python
class RunCreate(BaseModel):
    scope_id: UUID4  # Required, not Optional
    policy_version: str = "1.0.0"
    max_iterations: int = 100
    created_by: str = "system"
```

**Validation in** `securityflash/apps/api/routers/runs.py`:
- Lines 42-44: Validates scope exists
- Line 46: `ScopeLockService.enforce_locked(scope)` - Returns 400 if scope not locked

---

### D) ✅ Ensure V2 Error Handling Shows Full Responses

**Goal**: Make sure V2 proxy passes through complete error responses from V1.

**Status**: Already implemented correctly in `pentest-ai-platform/backend/api/proxy.py`:
```python
# Return V1's response unchanged (lines 77-82)
return Response(
    content=response.content,
    status_code=response.status_code,
    headers=dict(response.headers),
    media_type=response.headers.get("content-type")
)
```

**Result**: Error responses from V1 (including detail, loc, msg from FastAPI validation errors) are passed through unchanged to the React UI.

---

### E) ✅ Add Missing V1 Endpoints for Evidence and Executions

**Goal**: Add endpoints needed by Run Console UI.

**Changes**:

1. **Added evidence download endpoint** (`securityflash/apps/api/routers/evidence.py`):
   ```python
   @router.get("/{evidence_id}/download")
   def download_evidence(run_id: str, evidence_id: str, db: Session = Depends(get_db))
   ```
   - Generates presigned MinIO URL (valid for 1 hour)
   - Returns: `{evidence_id, artifact_uri, download_url, artifact_hash, expires_in_seconds}`

2. **Added presigned URL support** (`securityflash/apps/workers/storage/minio_store.py`):
   ```python
   def get_presigned_url(self, artifact_uri: str, expires_seconds: int = 3600) -> str
   ```
   - Parses S3 URI format: `s3://bucket/path`
   - Generates presigned URL using MinIO client

3. **Added get_download_url helper** (`securityflash/apps/api/services/evidence_service.py`):
   ```python
   def get_download_url(artifact_uri: str) -> str
   ```

4. **Added executions endpoint** (`securityflash/apps/api/routers/runs.py`):
   ```python
   @router.get("/runs/{run_id}/executions")
   def get_run_executions(run_id: str, db: Session = Depends(get_db))
   ```
   - Returns all action specs with status=EXECUTED
   - Formatted for UI with: id, tool, target, arguments, risk_score, approval_tier, timestamps

5. **Added report endpoints** (`securityflash/apps/api/routers/runs.py`):
   ```python
   @router.post("/runs/{run_id}/report/generate")
   @router.get("/runs/{run_id}/report")
   ```
   - Placeholder implementation (returns TODO status)
   - Structure ready for future report generation logic

**Existing endpoints confirmed working**:
- `GET /api/v1/runs/{run_id}/timeline` - Returns audit log events
- `GET /api/v1/runs/{run_id}/stats` - Returns action/evidence counts
- `GET /api/v1/runs/{run_id}/evidence` - Returns evidence list

---

### F) ✅ Complete Project CRUD

**Goal**: Add missing CRUD operations and primary_target_url field.

**Changes**:

1. **Added primary_target_url to model** (`securityflash/apps/api/models/project.py`):
   ```python
   primary_target_url = Column(String(500), nullable=True)  # Used to prefill first scope
   ```

2. **Updated schemas** (`securityflash/apps/api/schemas/project.py`):
   - Added `primary_target_url` to `ProjectCreate` (optional)
   - Created new `ProjectUpdate` schema with all optional fields
   - Added `primary_target_url` to `ProjectResponse`

3. **Updated create endpoint** (`securityflash/apps/api/routers/projects.py`):
   - Now accepts and stores `primary_target_url`

4. **Added PUT endpoint**:
   ```python
   @router.put("/{project_id}", response_model=ProjectResponse)
   def update_project(...)
   ```
   - Accepts `ProjectUpdate` schema
   - Updates only provided fields (partial update)
   - Logs to audit trail

5. **Added DELETE endpoint**:
   ```python
   @router.delete("/{project_id}", status_code=204)
   def delete_project(...)
   ```
   - Logs to audit trail before deletion
   - Cascade deletes scopes and runs (via FK constraints)

**Usage Flow**:
- Create project with `primary_target_url: "https://example.com"`
- UI prefills first scope targets with this URL
- Improves UX for quick pentest setup

---

### G) ✅ Create v2_smoke_flow.sh Test Script

**Goal**: Create automated test script that validates the complete user flow.

**Created**: `securityflash/scripts/v2_smoke_flow.sh`

**Test Flow**:
1. Create project with primary_target_url
2. Create scope with targets derived from project
3. Lock scope with signature
4. Create run (validates scope_id is locked)
5. Start run (explicit state transition CREATED -> RUNNING)
6. Fetch timeline (verify audit events)
7. Fetch stats (verify counts)
8. Fetch evidence (verify storage working)
9. Fetch executions (verify action tracking)

**Features**:
- Color-coded output (blue for steps, green for success)
- Error handling (exits on any failure)
- JSON validation (checks for null values)
- Summary output with:
  - Created IDs
  - UI links
  - API documentation links

**Usage**:
```bash
export SECURITYFLASH_API_URL=http://localhost:8000
./securityflash/scripts/v2_smoke_flow.sh
```

---

## Architecture Summary

### V1 (SecurityFlash Control Plane)
**Location**: `securityflash/`

**Responsibilities**:
- ✅ All data storage (PostgreSQL, Redis, MinIO)
- ✅ All business logic (Policy Engine, Approval Workflow, FSM)
- ✅ All audit logging (immutable audit trail)
- ✅ Agent runtime (autonomous action proposal)
- ✅ Worker runtime (safe tool execution)
- ✅ Evidence storage (immutable S3 artifacts)

**API Endpoints** (all under `/api/v1`):
- Projects: GET, POST, PUT, DELETE
- Scopes: GET list, GET, POST, PUT, DELETE, POST lock
- Runs: GET, POST, POST start, GET timeline, GET stats, GET executions, GET evidence
- Evidence: GET, POST, GET download
- Action Specs: GET, POST
- Approvals: GET, POST

---

### V2 (BFF - Backend For Frontend)
**Location**: `pentest-ai-platform/backend/`

**Responsibilities**:
- ✅ Stateless proxy ONLY
- ✅ No database
- ✅ No business logic
- ✅ No agents or workers
- ✅ No audit logs

**Implementation**:
- `main.py` - FastAPI app with health check
- `api/proxy.py` - Generic proxy utility (forwards all requests to V1)
- `api/*.py` - Route definitions (all call `proxy.proxy_request()`)
- `clients/securityflash_client.py` - V1 API client

**Proxy Behavior**:
- Forwards: method, path, headers, query params, body
- Returns: V1's status code, headers, body (unchanged)
- Timeout handling: 30 seconds default
- Error handling: 503 on connection error, 504 on timeout

---

## Next Steps

### H) Add Run Console UI (Pending)

**Requirements**:
1. Create `/runs/:runId` route in React
2. Show summary: status, started_at, completed_at, duration, scope_id, project_id
3. Live timeline: poll `GET /api/v1/runs/{run_id}/timeline` every 5s
4. Stats widget: `GET /api/v1/runs/{run_id}/stats`
5. Evidence list: `GET /api/v1/runs/{run_id}/evidence`
6. Executions list: `GET /api/v1/runs/{run_id}/executions`
7. Download button: Use `GET /api/v1/runs/{run_id}/evidence/{evidence_id}/download`

**UI Components Needed**:
- `RunConsole.tsx` - Main console page
- `RunTimeline.tsx` - Real-time event stream
- `RunStats.tsx` - Metrics dashboard
- `EvidenceViewer.tsx` - Evidence browser with download
- `ExecutionLog.tsx` - Action history

**NeuroSploit Vibe**:
- Terminal-style output for timeline
- Live updating stats (WebSocket or polling)
- Evidence preview with hash verification
- Action approval buttons inline

---

### I) Add Footer Links (Pending)

**Changes needed** in React UI:
```typescript
<Footer>
  <Link href={`${SECURITYFLASH_API_URL}/docs`}>V1 API Documentation</Link>
  <Link href={`${SECURITYFLASH_API_URL}/openapi.json`}>OpenAPI Spec</Link>
</Footer>
```

Where `SECURITYFLASH_API_URL = process.env.REACT_APP_SECURITYFLASH_API_URL`

---

## Testing the Changes

### Test V1 API Endpoints

```bash
# Set API URL
export SECURITYFLASH_API_URL=http://localhost:8000

# Run smoke test
./securityflash/scripts/v2_smoke_flow.sh
```

### Test V1 Directly

```bash
# Create project
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "customer_id": "test", "primary_target_url": "https://example.com", "created_by": "test"}'

# List scopes for project
curl http://localhost:8000/api/v1/projects/{project_id}/scopes

# Update scope (will fail if locked)
curl -X PUT http://localhost:8000/api/v1/projects/{project_id}/scopes/{scope_id} \
  -H "Content-Type: application/json" \
  -d '{...}'

# Delete project
curl -X DELETE http://localhost:8000/api/v1/projects/{project_id}
```

### Test V2 Proxy

```bash
# V2 proxies to V1
export SECURITYFLASH_API_URL=http://localhost:8000

# Start V2 BFF
cd pentest-ai-platform/backend
uvicorn main:app --port 3001

# Test via V2
curl http://localhost:3001/api/v1/projects
```

---

## File Changes Summary

### Modified Files

1. `securityflash/apps/api/routers/scopes.py` - Added GET list, PUT, DELETE
2. `securityflash/apps/api/routers/runs.py` - Added executions, report endpoints
3. `securityflash/apps/api/routers/evidence.py` - Added download endpoint
4. `securityflash/apps/api/routers/projects.py` - Added PUT, DELETE, primary_target_url
5. `securityflash/apps/api/models/project.py` - Added primary_target_url column
6. `securityflash/apps/api/schemas/project.py` - Added ProjectUpdate, primary_target_url
7. `securityflash/apps/api/services/evidence_service.py` - Added get_download_url
8. `securityflash/apps/workers/storage/minio_store.py` - Added get_presigned_url

### Created Files

1. `securityflash/scripts/v2_smoke_flow.sh` - End-to-end smoke test

### Moved Files

1. `pentest-ai-platform/backend/agents/` → `docs/legacy/agents/`
2. `pentest-ai-platform/backend/workers/` → `docs/legacy/workers/`
3. `pentest-ai-platform/backend/tools/` → `docs/legacy/tools/`
4. `pentest-ai-platform/backend/tools_experimental/` → `docs/legacy/tools_experimental/`
5. `pentest-ai-platform/backend/services/` → `docs/legacy/services/`
6. `pentest-ai-platform/backend/alembic.ini` → `docs/legacy/alembic.ini`
7. `pentest-ai-platform/backend/init_db.py` → `docs/legacy/init_db.py`
8. `pentest-ai-platform/backend/redis_client.py` → `docs/legacy/redis_client.py`

---

## Database Migrations Needed

### Add primary_target_url to projects table

```sql
ALTER TABLE projects
ADD COLUMN primary_target_url VARCHAR(500) NULL;
```

Or use Alembic:
```bash
cd securityflash
alembic revision --autogenerate -m "Add primary_target_url to projects"
alembic upgrade head
```

---

## Verification Checklist

- [x] V2 backend contains no agents, workers, tools, or services
- [x] V2 proxy forwards all requests to V1 unchanged
- [x] V1 scopes router has GET list, PUT, DELETE with lock enforcement
- [x] V1 runs router has executions, report endpoints
- [x] V1 evidence router has download endpoint with presigned URLs
- [x] V1 projects router has PUT, DELETE, primary_target_url
- [x] RunCreate schema requires scope_id (UUID4)
- [x] Smoke test script covers complete flow
- [ ] Database migration applied
- [ ] React UI updated with Run Console
- [ ] React UI updated with footer links

---

## Success Metrics

1. **V2 BFF is truly stateless**
   - No database connection in V2
   - No Redis connection in V2
   - No business logic in V2
   - All state lives in V1

2. **Complete CRUD for Projects and Scopes**
   - Create, Read, Update, Delete all working
   - Lock enforcement prevents updates/deletes
   - Audit trail tracks all changes

3. **Run Console has real data**
   - Timeline shows actual events
   - Stats show actual counts
   - Evidence list shows artifacts
   - Executions show what agent did

4. **Smoke test passes end-to-end**
   - Project creation works
   - Scope creation and locking works
   - Run creation and start works
   - Data retrieval works
