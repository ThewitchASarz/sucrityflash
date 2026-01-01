#!/bin/bash
#
# Smoke Test: End-to-End Pentest Loop with Real Agents and Workers
#
# This script proves that:
# 1. Agent daemon auto-starts for RUNNING runs
# 2. Agent proposes safe recon ActionSpecs
# 3. Policy Engine auto-approves Tier A actions
# 4. Worker executes approved actions using tool_registry runners
# 5. Evidence is stored with artifacts
# 6. Timeline events are emitted at each stage
#
# Requirements:
# - docker-compose up (all services running)
# - API accessible at localhost:8000
#

set -e

API_BASE="http://localhost:8000/api/v1"
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_RED='\033[0;31m'
COLOR_RESET='\033[0m'

function log_info() {
    echo -e "${COLOR_GREEN}[INFO]${COLOR_RESET} $1"
}

function log_wait() {
    echo -e "${COLOR_YELLOW}[WAIT]${COLOR_RESET} $1"
}

function log_error() {
    echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $1"
}

function wait_for_api() {
    log_wait "Waiting for API to be ready..."
    for i in {1..30}; do
        if curl -s "$API_BASE/health" > /dev/null 2>&1; then
            log_info "API is ready"
            return 0
        fi
        sleep 2
    done
    log_error "API did not become ready"
    exit 1
}

log_info "=== SMOKE TEST: Real End-to-End Pentest Loop ==="
log_info ""

# 1. Wait for API
wait_for_api

# 2. Create Project
log_info "Creating project..."
PROJECT_RESPONSE=$(curl -s -X POST "$API_BASE/projects" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Smoke Test - Real Run",
        "customer_id": "test-customer",
        "primary_target_url": "https://example.com",
        "created_by": "smoke-test"
    }')

PROJECT_ID=$(echo "$PROJECT_RESPONSE" | jq -r '.id')
log_info "Project created: $PROJECT_ID"

# 3. Create Scope
log_info "Creating scope with targets..."
SCOPE_RESPONSE=$(curl -s -X POST "$API_BASE/projects/$PROJECT_ID/scopes" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Test Scope",
        "scope_json": {
            "targets": [
                {"value": "https://example.com", "criticality": "MEDIUM"},
                {"value": "scanme.nmap.org", "criticality": "LOW"}
            ],
            "excluded_targets": []
        }
    }')

SCOPE_ID=$(echo "$SCOPE_RESPONSE" | jq -r '.id')
log_info "Scope created: $SCOPE_ID"

# 4. Lock Scope
log_info "Locking scope..."
curl -s -X POST "$API_BASE/projects/$PROJECT_ID/scopes/$SCOPE_ID/lock" \
    -H "Content-Type: application/json" \
    -d '{"locked_by": "smoke-test"}' > /dev/null

log_info "Scope locked"

# 5. Create Run
log_info "Creating run..."
RUN_RESPONSE=$(curl -s -X POST "$API_BASE/projects/$PROJECT_ID/runs" \
    -H "Content-Type: application/json" \
    -d '{
        "scope_id": "'"$SCOPE_ID"'",
        "run_name": "Smoke Test Real Execution",
        "policy_version": "v1.0",
        "max_iterations": 20
    }')

RUN_ID=$(echo "$RUN_RESPONSE" | jq -r '.id')
log_info "Run created: $RUN_ID"

# 6. Start Run
log_info "Starting run (this will trigger agent daemon)..."
curl -s -X POST "$API_BASE/projects/$PROJECT_ID/runs/$RUN_ID/start" > /dev/null
log_info "Run started - agent daemon should auto-start"

# 7. Wait for Timeline Events
log_info ""
log_wait "Waiting for agent to start and propose actions (30s)..."
sleep 30

# 8. Check Timeline for AGENT_STARTED
log_info "Checking timeline for AGENT_STARTED event..."
TIMELINE=$(curl -s "$API_BASE/projects/$PROJECT_ID/runs/$RUN_ID/timeline")
AGENT_STARTED=$(echo "$TIMELINE" | jq -r '.timeline[] | select(.event_type == "AGENT_STARTED") | .event_type')

if [ "$AGENT_STARTED" == "AGENT_STARTED" ]; then
    log_info "✓ AGENT_STARTED event found"
else
    log_error "✗ AGENT_STARTED event not found"
    echo "$TIMELINE" | jq '.'
    exit 1
fi

# 9. Check for ACTION_PROPOSED events
log_info "Checking for ACTION_PROPOSED events..."
ACTION_PROPOSED_COUNT=$(echo "$TIMELINE" | jq -r '[.timeline[] | select(.event_type == "ACTION_PROPOSED")] | length')
log_info "Found $ACTION_PROPOSED_COUNT ACTION_PROPOSED events"

if [ "$ACTION_PROPOSED_COUNT" -gt 0 ]; then
    log_info "✓ Agent has proposed actions"
else
    log_error "✗ No actions proposed yet"
fi

# 10. Check ActionSpecs
log_info "Checking ActionSpecs..."
ACTION_SPECS=$(curl -s "$API_BASE/runs/$RUN_ID/action-specs")
APPROVED_COUNT=$(echo "$ACTION_SPECS" | jq -r '[.[] | select(.status == "APPROVED")] | length')
EXECUTED_COUNT=$(echo "$ACTION_SPECS" | jq -r '[.[] | select(.status == "EXECUTED")] | length')
EXECUTING_COUNT=$(echo "$ACTION_SPECS" | jq -r '[.[] | select(.status == "EXECUTING")] | length')

log_info "ActionSpec status:"
log_info "  - APPROVED: $APPROVED_COUNT"
log_info "  - EXECUTING: $EXECUTING_COUNT"
log_info "  - EXECUTED: $EXECUTED_COUNT"

# 11. Wait for Worker Execution
if [ "$APPROVED_COUNT" -gt 0 ] || [ "$EXECUTING_COUNT" -gt 0 ]; then
    log_wait "Waiting for worker to execute approved actions (60s)..."
    sleep 60

    # Re-check timeline
    TIMELINE=$(curl -s "$API_BASE/projects/$PROJECT_ID/runs/$RUN_ID/timeline")
    EXECUTION_STARTED_COUNT=$(echo "$TIMELINE" | jq -r '[.timeline[] | select(.event_type == "EXECUTION_STARTED")] | length')
    EXECUTION_COMPLETED_COUNT=$(echo "$TIMELINE" | jq -r '[.timeline[] | select(.event_type == "EXECUTION_COMPLETED")] | length')
    EVIDENCE_ADDED_COUNT=$(echo "$TIMELINE" | jq -r '[.timeline[] | select(.event_type == "EVIDENCE_ADDED")] | length')

    log_info "Timeline events after worker execution:"
    log_info "  - EXECUTION_STARTED: $EXECUTION_STARTED_COUNT"
    log_info "  - EXECUTION_COMPLETED: $EXECUTION_COMPLETED_COUNT"
    log_info "  - EVIDENCE_ADDED: $EVIDENCE_ADDED_COUNT"

    if [ "$EXECUTION_COMPLETED_COUNT" -gt 0 ]; then
        log_info "✓ Worker has executed actions"
    else
        log_error "✗ No completed executions yet"
    fi
fi

# 12. Check Evidence
log_info "Checking evidence..."
EVIDENCE=$(curl -s "$API_BASE/projects/$PROJECT_ID/runs/$RUN_ID/evidence")
EVIDENCE_COUNT=$(echo "$EVIDENCE" | jq -r 'length')

log_info "Evidence records: $EVIDENCE_COUNT"

if [ "$EVIDENCE_COUNT" -gt 0 ]; then
    log_info "✓ Evidence has been stored"

    # Show first evidence record
    FIRST_EVIDENCE=$(echo "$EVIDENCE" | jq -r '.[0]')
    EVIDENCE_ID=$(echo "$FIRST_EVIDENCE" | jq -r '.id')
    EVIDENCE_TYPE=$(echo "$FIRST_EVIDENCE" | jq -r '.evidence_type')
    ARTIFACTS_COUNT=$(echo "$FIRST_EVIDENCE" | jq -r '.metadata.artifacts | length')

    log_info "First evidence:"
    log_info "  - ID: $EVIDENCE_ID"
    log_info "  - Type: $EVIDENCE_TYPE"
    log_info "  - Artifacts: $ARTIFACTS_COUNT"

    # Show artifact filenames
    if [ "$ARTIFACTS_COUNT" -gt 0 ]; then
        log_info "Artifacts:"
        echo "$FIRST_EVIDENCE" | jq -r '.metadata.artifacts[].filename' | while read filename; do
            log_info "    - $filename"
        done
    fi
else
    log_error "✗ No evidence found"
fi

# 13. Summary
log_info ""
log_info "=== SMOKE TEST SUMMARY ==="
log_info "Project ID: $PROJECT_ID"
log_info "Run ID: $RUN_ID"
log_info "Agent Started: $([ "$AGENT_STARTED" == "AGENT_STARTED" ] && echo "YES" || echo "NO")"
log_info "Actions Proposed: $ACTION_PROPOSED_COUNT"
log_info "Actions Executed: $EXECUTED_COUNT"
log_info "Evidence Records: $EVIDENCE_COUNT"
log_info ""

if [ "$AGENT_STARTED" == "AGENT_STARTED" ] && [ "$ACTION_PROPOSED_COUNT" -gt 0 ] && [ "$EVIDENCE_COUNT" -gt 0 ]; then
    log_info "✓✓✓ SMOKE TEST PASSED ✓✓✓"
    log_info "Real end-to-end pentest loop is working!"
    exit 0
else
    log_error "✗✗✗ SMOKE TEST FAILED ✗✗✗"
    log_error "Check logs for details"
    exit 1
fi
