# SecurityFlash Phase 2/3 - Higher Finding Yield with Governance

## Overview

Phase 2/3 implements:
- **Model Routing**: Context-aware LLM selection for planning, summarization, and triage
- **Automated Validators**: Deterministic finding generation from safe reconnaissance
- **Evidence-Backed Findings**: All findings require reproducibility evidence
- **ValidationPacks**: Human-executed high-risk testing procedures

**CRITICAL**: NO AUTONOMOUS EXPLOITATION. All high-risk actions require human approval and execution.

## Architecture

```
┌──────────────┐
│ Agent Runtime│  ← Uses ModelRouter for planning
│  (proposes)  │  ← Generates DRAFT findings via validators
└──────┬───────┘
       │ proposes ActionSpecs
       ↓
┌──────────────┐
│Control Plane │  ← Enforces policy & approval tiers
│  (governs)   │  ← Creates ValidationPacks for high-risk
└──────┬───────┘
       │ approved actions only
       ↓
┌──────────────┐
│Worker Runtime│  ← Executes SAFE tools only
│  (executes)  │  ← REFUSES manual_only=True actions
└──────┬───────┘
       │ generates Evidence
       ↓
┌──────────────┐
│  Validators  │  ← TLS, Headers, Exposure
│ (postprocess)│  ← Generates DRAFT findings
└──────┬───────┘
       │
       ↓
┌──────────────┐
│Human Reviewer│  ← Reviews findings
│  (validates) │  ← Executes ValidationPacks
└──────────────┘
```

## Components

### 1. ModelRouter (`apps/agents/model_router.py`)

Routes LLM calls based on task complexity:

```python
from apps.agents.model_router import ModelRouter

router = ModelRouter()

# Complex planning
response = router.generate(
    prompt="Build reconnaissance plan for https://example.com",
    mode="planner"  # Uses GPT-4
)

# Quick triage
response = router.generate(
    prompt="Classify this finding severity",
    mode="triage"  # Uses GPT-3.5-turbo
)

# Evidence summarization
response = router.generate(
    prompt="Summarize these httpx results",
    mode="summarizer"  # Uses GPT-4
)
```

**Telemetry**: Each response includes `model_name`, `tokens_est`, `latency_ms`.

### 2. Deterministic Validators (`apps/analysis/validators/`)

Generate DRAFT findings from safe tool outputs:

#### TLS Posture Validator
- Detects weak TLS versions (1.0, 1.1, SSL)
- Identifies weak ciphers (RC4, MD5, DES)
- Checks for missing HSTS header

#### Header Validator
- Missing CSP, X-Frame-Options, X-Content-Type-Options
- Insecure cookies (no Secure/HttpOnly flags)
- Missing security headers (5+ checks)

#### Exposure Validator
- High-risk ports (RDP, SMB, databases)
- Exposed administrative interfaces
- Service version disclosure

### 3. Findings (`apps/api/models/finding.py`)

```python
class FindingStatus:
    DRAFT = "DRAFT"              # Auto-generated, not reviewed
    NEEDS_REVIEW = "NEEDS_REVIEW"  # Flagged for human review
    CONFIRMED = "CONFIRMED"      # Validated with evidence
    REJECTED = "REJECTED"        # False positive
```

**Requirements for CONFIRMED status:**
- `evidence_ids`: List of Evidence UUIDs
- `reproducibility_md`: Step-by-step reproduction instructions
- Human reviewer validation

### 4. ValidationPacks (`apps/api/models/validation_pack.py`)

High-risk testing procedures for HUMAN execution only.

```python
class ValidationPackStatus:
    PENDING_APPROVAL = "PENDING_APPROVAL"
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"
```

**Structure:**
```json
{
  "title": "Test SQL Injection on /api/users",
  "category": "INJECTION_PROBE",
  "risk_level": "HIGH",
  "instructions_md": "1. Verify target is in scope\n2. Test with safe payloads...",
  "command_templates": [
    {"tool": "curl", "template": "curl -X POST ... -d \"username='OR'1'='1\""}
  ],
  "required_evidence_types": ["request_response", "screenshot"],
  "evidence_checklist_md": "- [ ] Verified error message\n- [ ] Confirmed injection",
  "safety_notes": "Do NOT use destructive payloads. Test read-only queries first.",
  "target_must_match_scope": true
}
```

## Workflow

### Phase 1: Safe Reconnaissance (Automated)

1. Agent proposes reconnaissance actions (httpx, nmap)
2. Reviewer approves Tier C/B actions
3. Worker executes tools
4. Evidence generated automatically

### Phase 2: Finding Generation (Automated)

5. Validators process evidence
6. DRAFT findings created with:
   - Severity (CRITICAL → INFO)
   - Category (RECON, CONFIG, EXPOSURE, etc.)
   - Evidence IDs
   - Reproducibility instructions

### Phase 3: Validation (Human)

7. Reviewer examines DRAFT findings
8. For high-risk findings, create ValidationPack
9. Human tester executes validation steps
10. Attach evidence to ValidationPack
11. Mark finding as CONFIRMED or REJECTED

## API Endpoints

### Findings

```bash
# List findings for a run
GET /api/v1/runs/{run_id}/findings?status=DRAFT

# Get specific finding
GET /api/v1/findings/{finding_id}

# Update finding status
PATCH /api/v1/findings/{finding_id}
{
  "status": "CONFIRMED",
  "reviewer_id": "user@example.com"
}
```

### ValidationPacks

```bash
# Create ValidationPack
POST /api/v1/runs/{run_id}/validation-packs
{
  "finding_id": "uuid",
  "title": "Validate XSS in search parameter",
  "category": "INJECTION_PROBE",
  "risk_level": "HIGH",
  "instructions_md": "...",
  "created_by": "agent-orchestrator"
}

# List ValidationPacks
GET /api/v1/runs/{run_id}/validation-packs?status=OPEN

# Attach evidence
POST /api/v1/runs/{run_id}/validation-packs/{pack_id}/attach-evidence
{
  "evidence_ids": ["evidence-uuid-1", "evidence-uuid-2"]
}

# Mark complete
POST /api/v1/runs/{run_id}/validation-packs/{pack_id}/complete
{
  "completed_by": "user@example.com",
  "execution_notes": "Confirmed XSS with PoC payload..."
}
```

## Safety Gates

### Worker Enforcement

Worker **MUST REFUSE** actions with:
- `manual_only=True` in ToolSpec
- `category=VALIDATION_HIGH_RISK` in ActionSpec
- Any ValidationPack execution requests

```python
# In worker/tool_registry.py
if tool_spec.manual_only:
    raise ValueError(f"Tool {tool_name} is manual-only. Worker cannot execute.")

# In worker/runner.py
if action.category == "VALIDATION_HIGH_RISK":
    logger.error(f"CRITICAL: Worker refusing high-risk action {action.id}")
    mark_action_failed(action, "HIGH_RISK_MANUAL_ONLY")
    return
```

### Scope Validation

Before ANY ValidationPack execution:
1. Verify `target_must_match_scope=True`
2. Check target against scope.scope_json.targets
3. Enforce rate limits from `rate_limit_seconds`
4. Log all validation attempts for audit

## Database Migration

```bash
# Apply Phase 2/3 migration
psql -U postgres -d securityflash < migrations/003_add_validation_packs.sql
```

## Example: End-to-End Flow

```python
# 1. Agent reconnaissance (automated)
agent.propose_action(tool="httpx", target="https://example.com")
# → ActionSpec created, approved, executed
# → Evidence created

# 2. Validator processing (automated)
from apps.analysis.findings_postprocessor import FindingsPostprocessor

processor = FindingsPostprocessor()
findings = processor.process_evidence(
    evidence=evidence_obj,
    run_id=run.id,
    project_id=project.id,
    scope_id=scope.id,
    db=db
)
# → DRAFT findings created: "Missing HSTS Header", "Weak TLS 1.0", etc.

# 3. Human review
reviewer.review_finding(finding_id)
# Reviewer sees:
# - Title: "Missing Content-Security-Policy Header"
# - Severity: MEDIUM
# - Evidence: Link to httpx output
# - Reproducibility: Step-by-step curl command

# 4. Create ValidationPack for high-risk finding
if finding.severity in ["HIGH", "CRITICAL"]:
    validation_pack = create_validation_pack(
        title=f"Validate {finding.title}",
        instructions_md=generate_validation_steps(finding),
        required_evidence=["request_response", "screenshot"]
    )

# 5. Human execution (manual)
tester.execute_validation_pack(validation_pack)
# - Follows instructions
# - Captures evidence
# - Marks complete

# 6. Confirm finding
finding.status = FindingStatus.CONFIRMED
finding.evidence_ids.extend(validation_pack.evidence_ids)
db.commit()
```

## Testing

```bash
# Test validators
pytest apps/analysis/validators/ -v

# Test findings postprocessor
pytest apps/analysis/test_findings_postprocessor.py -v

# Test ValidationPack API
pytest apps/api/routers/test_validation_packs.py -v
```

## Monitoring

New metrics:
- `model_router_calls_total{mode, model}` - LLM usage by mode
- `findings_generated_total{severity, validator}` - Finding yield
- `validation_packs_created_total{risk_level}` - High-risk validations
- `validation_packs_completed_total{status}` - Completion rate

## Security Considerations

1. **NO Exploit Code**: ValidationPacks contain instructions, not executable exploits
2. **Scope Enforcement**: All targets validated against locked scope
3. **Rate Limiting**: ValidationPacks include rate limit constraints
4. **Audit Trail**: All validation attempts logged
5. **Human-in-Loop**: High-risk actions require human execution

## Future Enhancements

- ML-based finding prioritization
- Automated evidence correlation
- ValidationPack templates library
- Integration with SIEM for real-time alerting
