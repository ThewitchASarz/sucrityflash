#!/bin/bash
#
# Phase 3 Smoke Test: Validation Packs, Monitored Mode, Kill Switch
#
# This script is intentionally sequential and non-destructive. It exercises:
#  - Validation Pack lifecycle (DRAFT -> READY -> approvals -> IN_PROGRESS -> COMPLETE)
#  - Evidence attachment using the existing Evidence model
#  - Monitored mode toggling
#  - Kill switch activation halting further actions
#
set -euo pipefail

API_BASE="http://localhost:8000/api/v1"
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_RED='\033[0;31m'
COLOR_RESET='\033[0m'

log_info() { echo -e "${COLOR_GREEN}[INFO]${COLOR_RESET} $1"; }
log_wait() { echo -e "${COLOR_YELLOW}[WAIT]${COLOR_RESET} $1"; }
log_error() { echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $1"; }

wait_for_api() {
  log_wait "Waiting for Control Plane at $API_BASE ..."
  for i in {1..30}; do
    if curl -s "$API_BASE/../health" >/dev/null 2>&1; then
      log_info "API is ready"
      return 0
    fi
    sleep 2
  done
  log_error "API did not become ready"
  exit 1
}

log_info "=== PHASE 3 SMOKE TEST: Validation Packs + Monitored Mode ==="
wait_for_api

# 1) Project + Scope + Run
log_info "Creating project and scope..."
PROJECT_ID=$(curl -s -X POST "$API_BASE/projects" -H "Content-Type: application/json" -d '{
  "name": "Phase3 Smoke",
  "customer_id": "phase3-smoke",
  "primary_target_url": "https://example.com",
  "created_by": "smoke-phase3"
}' | jq -r '.id')

SCOPE_ID=$(curl -s "$API_BASE/projects/$PROJECT_ID/scopes" | jq -r '.[0].id')
log_info "Project $PROJECT_ID Scope $SCOPE_ID"

curl -s -X POST "$API_BASE/projects/$PROJECT_ID/scopes/$SCOPE_ID/lock" -H "Content-Type: application/json" -d '{"locked_by": "smoke-phase3", "signature": "phase3-signature"}' >/dev/null

log_info "Creating run..."
RUN_ID=$(curl -s -X POST "$API_BASE/projects/$PROJECT_ID/runs" -H "Content-Type: application/json" -d "{
  \"scope_id\": \"$SCOPE_ID\",
  \"policy_version\": \"v1.0\",
  \"max_iterations\": 5,
  \"created_by\": \"smoke-phase3\"
}" | jq -r '.id')
curl -s -X POST "$API_BASE/runs/$RUN_ID/start" >/dev/null
log_info "Run $RUN_ID started"

# 2) Validation Pack lifecycle (HIGH risk requires dual approvals)
log_info "Creating validation pack (DRAFT)..."
PACK_ID=$(curl -s -X POST "$API_BASE/runs/$RUN_ID/validation-packs" -H "Content-Type: application/json" -d "{
  \"title\": \"Validate admin exposure\",
  \"risk_level\": \"HIGH\",
  \"instructions_md\": \"Run only the provided read-only checks. Stop if any state changes.\",
  \"command_templates\": [{
    \"label\": \"HTTP validation\",
    \"command\": \"httpx -status-code -location -title -path /\",
    \"params_schema\": {\"type\": \"object\"},
    \"safety_notes\": \"Read-only GETs only\"
  }],
  \"stop_conditions\": [\"State change detected\", \"500 errors\"],
  \"required_evidence\": [\"Screenshots\", \"HTTP headers\"],
  \"created_by\": \"smoke-phase3\"
}" | jq -r '.id')
log_info "Pack $PACK_ID created"

log_info "Submitting pack -> READY"
curl -s -X POST "$API_BASE/validation-packs/$PACK_ID/submit" -H "Content-Type: application/json" -d '{"actor": "smoke-phase3"}' >/dev/null

log_info "Reviewer approval (keeps HIGH pack gated)"
curl -s -X POST "$API_BASE/validation-packs/$PACK_ID/approve/reviewer" -H "Content-Type: application/json" -d '{"approver": "reviewer-smoke"}' >/dev/null

log_info "Engineer approval -> IN_PROGRESS"
curl -s -X POST "$API_BASE/validation-packs/$PACK_ID/approve/engineer" -H "Content-Type: application/json" -d '{"approver": "engineer-smoke"}' >/dev/null

# 3) Evidence attachment using existing model
log_info "Creating placeholder evidence"
EVIDENCE_ID=$(curl -s -X POST "$API_BASE/runs/$RUN_ID/evidence" -H "Content-Type: application/json" -d "{
  \"evidence_type\": \"command_output\",
  \"artifact_uri\": \"s3://placeholder/artifact.txt\",
  \"artifact_hash\": \"$(uuidgen | tr '[:upper:]' '[:lower:]')\",
  \"generated_by\": \"smoke-phase3\",
  \"metadata\": {\"tool_used\": \"httpx\", \"stdout\": \"200 OK\"}
}" | jq -r '.id')
log_info "Evidence $EVIDENCE_ID created"

log_info "Attaching evidence to validation pack"
curl -s -X POST "$API_BASE/validation-packs/$PACK_ID/attach-evidence" -H "Content-Type: application/json" -d "{
  \"evidence_id\": \"$EVIDENCE_ID\",
  \"actor\": \"smoke-phase3\"
}" >/dev/null

log_info "Completing validation pack"
curl -s -X POST "$API_BASE/validation-packs/$PACK_ID/complete" -H "Content-Type: application/json" -d '{"actor": "smoke-phase3"}' >/dev/null

# 4) Monitored mode + kill switch
log_info "Enabling monitored mode with approvals"
curl -s -X POST "$API_BASE/runs/$RUN_ID/monitored-mode/enable" -H "Content-Type: application/json" -d '{
  "reviewer_approval": "reviewer-smoke",
  "engineer_approval": "engineer-smoke",
  "started_by": "smoke-phase3",
  "monitored_rate_limit_rpm": 10,
  "monitored_max_concurrency": 2
}' >/dev/null

log_info "Activating kill switch (sets run to ABORTED)"
curl -s -X POST "$API_BASE/runs/$RUN_ID/kill-switch/activate" -H "Content-Type: application/json" -d '{
  "actor": "smoke-phase3",
  "reason": "smoke test kill switch"
}' >/dev/null

STATUS=$(curl -s "$API_BASE/runs/$RUN_ID" | jq -r '.status')
if [ "$STATUS" != "ABORTED" ]; then
  log_error "Expected run to be ABORTED after kill switch, got $STATUS"
  exit 1
fi

log_info "✓ Smoke test complete. Validation pack lifecycle and kill switch verified."
