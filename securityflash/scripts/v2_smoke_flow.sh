#!/bin/bash
# SecurityFlash V2 Smoke Test Flow
# Tests the complete flow: create project -> create scope -> lock -> create run -> start -> fetch data

set -e  # Exit on any error

API_URL="${SECURITYFLASH_API_URL:-http://localhost:8000}"
PROJECT_NAME="Smoke Test Project $(date +%s)"
CUSTOMER_ID="test-customer"
PRIMARY_TARGET="https://example.com"
CREATOR="smoke-test-user"

echo "=========================================="
echo "SecurityFlash V2 Smoke Test Flow"
echo "=========================================="
echo "API URL: $API_URL"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Create Project
echo -e "${BLUE}Step 1: Creating project...${NC}"
PROJECT_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/projects" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$PROJECT_NAME\",
    \"customer_id\": \"$CUSTOMER_ID\",
    \"primary_target_url\": \"$PRIMARY_TARGET\",
    \"created_by\": \"$CREATOR\"
  }")

PROJECT_ID=$(echo "$PROJECT_RESPONSE" | jq -r '.id')
if [ "$PROJECT_ID" == "null" ] || [ -z "$PROJECT_ID" ]; then
  echo "❌ Failed to create project"
  echo "$PROJECT_RESPONSE" | jq '.'
  exit 1
fi
echo -e "${GREEN}✅ Project created: $PROJECT_ID${NC}"
echo ""

# Step 2: Create Scope
echo -e "${BLUE}Step 2: Creating scope...${NC}"
SCOPE_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/projects/$PROJECT_ID/scopes" \
  -H "Content-Type: application/json" \
  -d "{
    \"scope_type\": \"web_application\",
    \"targets\": [
      {
        \"type\": \"url\",
        \"value\": \"$PRIMARY_TARGET\",
        \"ports\": [80, 443]
      }
    ],
    \"excluded_targets\": [],
    \"attack_vectors_allowed\": [\"reconnaissance\", \"vulnerability_scanning\"],
    \"attack_vectors_prohibited\": [\"denial_of_service\", \"social_engineering\"],
    \"approved_tools\": [\"nmap\", \"httpx\"],
    \"time_restrictions\": null
  }")

SCOPE_ID=$(echo "$SCOPE_RESPONSE" | jq -r '.id')
if [ "$SCOPE_ID" == "null" ] || [ -z "$SCOPE_ID" ]; then
  echo "❌ Failed to create scope"
  echo "$SCOPE_RESPONSE" | jq '.'
  exit 1
fi
echo -e "${GREEN}✅ Scope created: $SCOPE_ID${NC}"
echo ""

# Step 3: Lock Scope
echo -e "${BLUE}Step 3: Locking scope...${NC}"
LOCK_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/projects/$PROJECT_ID/scopes/$SCOPE_ID/lock" \
  -H "Content-Type: application/json" \
  -d "{
    \"locked_by\": \"$CREATOR\",
    \"signature\": \"smoke-test-signature-$(date +%s)\"
  }")

LOCKED_AT=$(echo "$LOCK_RESPONSE" | jq -r '.locked_at')
if [ "$LOCKED_AT" == "null" ] || [ -z "$LOCKED_AT" ]; then
  echo "❌ Failed to lock scope"
  echo "$LOCK_RESPONSE" | jq '.'
  exit 1
fi
echo -e "${GREEN}✅ Scope locked at: $LOCKED_AT${NC}"
echo ""

# Step 4: Create Run
echo -e "${BLUE}Step 4: Creating run...${NC}"
RUN_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/projects/$PROJECT_ID/runs" \
  -H "Content-Type: application/json" \
  -d "{
    \"scope_id\": \"$SCOPE_ID\",
    \"policy_version\": \"1.0.0\",
    \"max_iterations\": 10,
    \"created_by\": \"$CREATOR\"
  }")

RUN_ID=$(echo "$RUN_RESPONSE" | jq -r '.id')
if [ "$RUN_ID" == "null" ] || [ -z "$RUN_ID" ]; then
  echo "❌ Failed to create run"
  echo "$RUN_RESPONSE" | jq '.'
  exit 1
fi
RUN_STATUS=$(echo "$RUN_RESPONSE" | jq -r '.status')
echo -e "${GREEN}✅ Run created: $RUN_ID${NC}"
echo "   Status: $RUN_STATUS"
echo ""

# Step 5: Start Run
echo -e "${BLUE}Step 5: Starting run...${NC}"
START_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/runs/$RUN_ID/start" \
  -H "Content-Type: application/json" \
  -d "{}")

STARTED_AT=$(echo "$START_RESPONSE" | jq -r '.started_at')
RUNNING_STATUS=$(echo "$START_RESPONSE" | jq -r '.status')
if [ "$STARTED_AT" == "null" ] || [ -z "$STARTED_AT" ]; then
  echo "❌ Failed to start run"
  echo "$START_RESPONSE" | jq '.'
  exit 1
fi
echo -e "${GREEN}✅ Run started at: $STARTED_AT${NC}"
echo "   Status: $RUNNING_STATUS"
echo ""

# Step 6: Fetch Timeline
echo -e "${BLUE}Step 6: Fetching timeline...${NC}"
TIMELINE_RESPONSE=$(curl -s "$API_URL/api/v1/runs/$RUN_ID/timeline")
TIMELINE_COUNT=$(echo "$TIMELINE_RESPONSE" | jq '. | length')
echo -e "${GREEN}✅ Timeline events: $TIMELINE_COUNT${NC}"
if [ "$TIMELINE_COUNT" -gt 0 ]; then
  echo "   Latest events:"
  echo "$TIMELINE_RESPONSE" | jq -r '.[-3:] | .[] | "   - [\(.timestamp)] \(.event_type)"'
fi
echo ""

# Step 7: Fetch Stats
echo -e "${BLUE}Step 7: Fetching stats...${NC}"
STATS_RESPONSE=$(curl -s "$API_URL/api/v1/runs/$RUN_ID/stats")
echo -e "${GREEN}✅ Run statistics:${NC}"
echo "$STATS_RESPONSE" | jq '{
  action_specs: .action_specs_count,
  pending_approvals: .pending_approvals_count,
  approved: .approved_count,
  executed: .executed_count,
  evidence: .evidence_count,
  last_activity: .last_activity_at
}'
echo ""

# Step 8: Fetch Evidence
echo -e "${BLUE}Step 8: Fetching evidence...${NC}"
EVIDENCE_RESPONSE=$(curl -s "$API_URL/api/v1/runs/$RUN_ID/evidence")
EVIDENCE_COUNT=$(echo "$EVIDENCE_RESPONSE" | jq '. | length')
echo -e "${GREEN}✅ Evidence records: $EVIDENCE_COUNT${NC}"
if [ "$EVIDENCE_COUNT" -gt 0 ]; then
  echo "   Sample evidence:"
  echo "$EVIDENCE_RESPONSE" | jq -r '.[0:3] | .[] | "   - [\(.evidence_type)] \(.artifact_hash[0:16])..."'
fi
echo ""

# Step 9: Fetch Executions
echo -e "${BLUE}Step 9: Fetching executions...${NC}"
EXECUTIONS_RESPONSE=$(curl -s "$API_URL/api/v1/runs/$RUN_ID/executions")
EXECUTIONS_COUNT=$(echo "$EXECUTIONS_RESPONSE" | jq '. | length')
echo -e "${GREEN}✅ Executed actions: $EXECUTIONS_COUNT${NC}"
if [ "$EXECUTIONS_COUNT" -gt 0 ]; then
  echo "   Sample executions:"
  echo "$EXECUTIONS_RESPONSE" | jq -r '.[0:3] | .[] | "   - \(.tool) -> \(.target)"'
fi
echo ""

# Summary
echo "=========================================="
echo -e "${GREEN}✅ SMOKE TEST PASSED${NC}"
echo "=========================================="
echo "Project ID:  $PROJECT_ID"
echo "Scope ID:    $SCOPE_ID"
echo "Run ID:      $RUN_ID"
echo ""
echo "View in UI:"
echo "  - Project: http://localhost:3000/projects/$PROJECT_ID"
echo "  - Run Console: http://localhost:3000/runs/$RUN_ID"
echo ""
echo "View in V1 API:"
echo "  - OpenAPI Docs: $API_URL/docs"
echo "  - Run Status: $API_URL/api/v1/runs/$RUN_ID"
echo ""
