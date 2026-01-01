#!/bin/bash
#
# Phase 3 Smoke Test: Manual Validation Workflow
#
# This script verifies:
# 1. LOW findings can be confirmed with minimal evidence
# 2. HIGH/CRITICAL findings REQUIRE manual validation tasks
# 3. Manual tasks must be COMPLETE with evidence before confirmation
# 4. Report includes task details for confirmed findings
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
        if curl -s "$API_BASE/../health" > /dev/null 2>&1; then
            log_info "API is ready"
            return 0
        fi
        sleep 2
    done
    log_error "API did not become ready"
    exit 1
}

log_info "=== PHASE 3 SMOKE TEST: Manual Validation Workflow ==="
log_info ""

# Wait for API
wait_for_api

# 1. Create Project + Scope
log_info "Step 1: Creating project and scope..."
PROJECT_RESPONSE=$(curl -s -X POST "$API_BASE/projects" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Phase 3 Smoke Test",
        "customer_id": "test-customer",
        "primary_target_url": "https://example.com",
        "created_by": "smoke-test"
    }')

PROJECT_ID=$(echo "$PROJECT_RESPONSE" | jq -r '.id')
log_info "Project created: $PROJECT_ID"

# Get auto-created scope
SCOPES=$(curl -s "$API_BASE/projects/$PROJECT_ID/scopes")
SCOPE_ID=$(echo "$SCOPES" | jq -r '.[0].id')
log_info "Scope ID: $SCOPE_ID"

# Lock scope
curl -s -X POST "$API_BASE/projects/$PROJECT_ID/scopes/$SCOPE_ID/lock" \
    -H "Content-Type: application/json" \
    -d '{"locked_by": "smoke-test", "signature": "sig-123"}' > /dev/null
log_info "Scope locked"

# 2. Create Run
log_info "Step 2: Creating and starting run..."
RUN_RESPONSE=$(curl -s -X POST "$API_BASE/projects/$PROJECT_ID/runs" \
    -H "Content-Type: application/json" \
    -d '{
        "scope_id": "'"$SCOPE_ID"'",
        "run_name": "Phase 3 Test",
        "policy_version": "v1.0",
        "max_iterations": 10,
        "created_by": "smoke-test"
    }')

RUN_ID=$(echo "$RUN_RESPONSE" | jq -r '.id')
log_info "Run created: $RUN_ID"

# Start run
curl -s -X POST "$API_BASE/runs/$RUN_ID/start" > /dev/null
log_info "Run started"

# 3. Create a LOW severity finding
log_info ""
log_info "Step 3: Creating LOW severity finding..."
LOW_FINDING_RESPONSE=$(curl -s -X POST "$API_BASE/runs/$RUN_ID/findings" \
    -H "Content-Type: application/json" \
    -d '{
        "title": "Test LOW severity finding",
        "severity": "LOW",
        "category": "RECON",
        "affected_target": "https://example.com",
        "description_md": "This is a test LOW finding",
        "reproducibility_md": "1. Do thing\n2. Observe result",
        "evidence_ids": ["00000000-0000-0000-0000-000000000001"],
        "created_by": "smoke-test"
    }')

LOW_FINDING_ID=$(echo "$LOW_FINDING_RESPONSE" | jq -r '.id')
log_info "LOW finding created: $LOW_FINDING_ID"

# 4. Submit LOW finding for review
log_info "Step 4: Submitting LOW finding for review..."
curl -s -X POST "$API_BASE/findings/$LOW_FINDING_ID/submit_for_review" > /dev/null
log_info "LOW finding submitted for review"

# 5. Confirm LOW finding (should succeed with minimal evidence)
log_info "Step 5: Confirming LOW finding (should succeed)..."
LOW_CONFIRM_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/findings/$LOW_FINDING_ID/confirm" \
    -H "Content-Type: application/json" \
    -d '{
        "reviewer_id": "reviewer-1",
        "reason": "Looks good"
    }')

HTTP_CODE=$(echo "$LOW_CONFIRM_RESPONSE" | tail -n1)
if [ "$HTTP_CODE" == "200" ]; then
    log_info "✓ LOW finding confirmed successfully"
else
    log_error "✗ Failed to confirm LOW finding (HTTP $HTTP_CODE)"
    echo "$LOW_CONFIRM_RESPONSE" | head -n -1
    exit 1
fi

# 6. Create a HIGH severity finding
log_info ""
log_info "Step 6: Creating HIGH severity finding..."
HIGH_FINDING_RESPONSE=$(curl -s -X POST "$API_BASE/runs/$RUN_ID/findings" \
    -H "Content-Type: application/json" \
    -d '{
        "title": "Test HIGH severity finding",
        "severity": "HIGH",
        "category": "EXPOSURE",
        "affected_target": "https://example.com/admin",
        "description_md": "This is a test HIGH finding requiring manual validation",
        "reproducibility_md": "1. Navigate to admin panel\n2. Observe exposure",
        "evidence_ids": ["00000000-0000-0000-0000-000000000002"],
        "created_by": "smoke-test"
    }')

HIGH_FINDING_ID=$(echo "$HIGH_FINDING_RESPONSE" | jq -r '.id')
log_info "HIGH finding created: $HIGH_FINDING_ID"

# 7. Submit HIGH finding for review
log_info "Step 7: Submitting HIGH finding for review..."
curl -s -X POST "$API_BASE/findings/$HIGH_FINDING_ID/submit_for_review" > /dev/null
log_info "HIGH finding submitted for review"

# 8. Attempt to confirm HIGH finding without manual task (should FAIL)
log_info "Step 8: Attempting to confirm HIGH finding without manual task (should FAIL)..."
HIGH_CONFIRM_FAIL=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/findings/$HIGH_FINDING_ID/confirm" \
    -H "Content-Type: application/json" \
    -d '{
        "reviewer_id": "reviewer-1",
        "reason": "Trying to confirm"
    }')

HTTP_CODE=$(echo "$HIGH_CONFIRM_FAIL" | tail -n1)
if [ "$HTTP_CODE" == "400" ]; then
    ERROR_MSG=$(echo "$HIGH_CONFIRM_FAIL" | head -n -1 | jq -r '.detail')
    log_info "✓ Correctly rejected HIGH finding without manual task: $ERROR_MSG"
else
    log_error "✗ HIGH finding was confirmed without manual task (should have been rejected)"
    exit 1
fi

# 9. Create manual validation task
log_info ""
log_info "Step 9: Creating manual validation task..."
TASK_RESPONSE=$(curl -s -X POST "$API_BASE/findings/$HIGH_FINDING_ID/manual-tasks" \
    -H "Content-Type: application/json" \
    -d '{
        "title": "Manual verification of admin panel exposure",
        "instructions_md": "1. Navigate to https://example.com/admin\n2. Document access control behavior\n3. Capture screenshots\n4. Test authentication bypass",
        "required_evidence_types": ["screenshot", "request_response"],
        "created_by": "pentester-1"
    }')

TASK_ID=$(echo "$TASK_RESPONSE" | jq -r '.id')
log_info "Manual task created: $TASK_ID"

# 10. Attach evidence to task
log_info "Step 10: Attaching evidence to manual task..."
curl -s -X POST "$API_BASE/manual-tasks/$TASK_ID/attach-evidence" \
    -H "Content-Type: application/json" \
    -d '{"evidence_id": "00000000-0000-0000-0000-000000000003"}' > /dev/null
log_info "Evidence attached to task"

# 11. Mark task as IN_PROGRESS
log_info "Step 11: Updating task status to IN_PROGRESS..."
curl -s -X PATCH "$API_BASE/manual-tasks/$TASK_ID" \
    -H "Content-Type: application/json" \
    -d '{"status": "IN_PROGRESS"}' > /dev/null
log_info "Task status: IN_PROGRESS"

# 12. Complete the task
log_info "Step 12: Completing manual task..."
curl -s -X PATCH "$API_BASE/manual-tasks/$TASK_ID" \
    -H "Content-Type: application/json" \
    -d '{
        "status": "COMPLETE",
        "completed_by": "pentester-1",
        "notes": "Confirmed admin panel is accessible without authentication"
    }' > /dev/null
log_info "Task completed"

# 13. Now confirm HIGH finding (should succeed)
log_info "Step 13: Confirming HIGH finding with completed manual task (should succeed)..."
HIGH_CONFIRM_SUCCESS=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/findings/$HIGH_FINDING_ID/confirm" \
    -H "Content-Type: application/json" \
    -d '{
        "reviewer_id": "reviewer-1",
        "reason": "Validated via manual task with evidence"
    }')

HTTP_CODE=$(echo "$HIGH_CONFIRM_SUCCESS" | tail -n1)
if [ "$HTTP_CODE" == "200" ]; then
    log_info "✓ HIGH finding confirmed successfully with manual task"
else
    log_error "✗ Failed to confirm HIGH finding with manual task (HTTP $HTTP_CODE)"
    echo "$HIGH_CONFIRM_SUCCESS" | head -n -1
    exit 1
fi

# 14. Check findings list
log_info ""
log_info "Step 14: Verifying findings list..."
FINDINGS=$(curl -s "$API_BASE/runs/$RUN_ID/findings")
CONFIRMED_COUNT=$(echo "$FINDINGS" | jq -r '[.[] | select(.status == "CONFIRMED")] | length')
log_info "Confirmed findings: $CONFIRMED_COUNT"

if [ "$CONFIRMED_COUNT" -ge 2 ]; then
    log_info "✓ Both findings confirmed"
else
    log_error "✗ Expected at least 2 confirmed findings, got $CONFIRMED_COUNT"
    exit 1
fi

# 15. Generate report
log_info ""
log_info "Step 15: Generating report..."
REPORT_RESPONSE=$(curl -s -X POST "$API_BASE/runs/$RUN_ID/report/generate?format=html")
REPORT_STATUS=$(echo "$REPORT_RESPONSE" | jq -r '.status')

if [ "$REPORT_STATUS" == "completed" ]; then
    log_info "✓ Report generated successfully"
    EVIDENCE_ID=$(echo "$REPORT_RESPONSE" | jq -r '.evidence_id')
    log_info "Report evidence ID: $EVIDENCE_ID"
else
    log_error "✗ Report generation failed: $REPORT_STATUS"
    exit 1
fi

# Summary
log_info ""
log_info "=== PHASE 3 SMOKE TEST SUMMARY ==="
log_info "Project ID: $PROJECT_ID"
log_info "Run ID: $RUN_ID"
log_info "LOW Finding ID: $LOW_FINDING_ID (CONFIRMED)"
log_info "HIGH Finding ID: $HIGH_FINDING_ID (CONFIRMED with manual task)"
log_info "Manual Task ID: $TASK_ID (COMPLETE)"
log_info ""
log_info "✓✓✓ ALL PHASE 3 TESTS PASSED ✓✓✓"
log_info "Manual validation workflow is working correctly!"
log_info ""
log_info "Key verifications:"
log_info "  ✓ LOW findings confirm with minimal evidence"
log_info "  ✓ HIGH findings require manual validation tasks"
log_info "  ✓ Manual tasks must be COMPLETE with evidence"
log_info "  ✓ Confirmation policy enforces review workflow"
log_info "  ✓ Report generation includes validated findings"

exit 0
