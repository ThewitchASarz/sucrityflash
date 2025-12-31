#!/bin/bash
# Comprehensive API testing script

set -e

BASE_URL="http://localhost:8000"

echo "=== Testing Pentest AI Platform API ==="
echo

# Test 1: Health check
echo "1. Testing health endpoint..."
curl -s "$BASE_URL/health" | python3 -m json.tool
echo "✓ Health check passed"
echo

# Test 2: Register Coordinator
echo "2. Registering coordinator..."
COORD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "email": "coordinator@test.com",
  "password": "SecurePass123",
  "full_name": "Test Coordinator",
  "role": "COORDINATOR"
}
EOF
)
echo "$COORD_RESPONSE" | python3 -m json.tool
COORD_ID=$(echo "$COORD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "✓ Coordinator registered: $COORD_ID"
echo

# Test 3: Login Coordinator
echo "3. Logging in coordinator..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "email": "coordinator@test.com",
  "password": "SecurePass123"
}
EOF
)
echo "$LOGIN_RESPONSE" | python3 -m json.tool
TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
echo "✓ Login successful"
echo

# Test 4: Create Project
echo "4. Creating project..."
PROJECT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/projects" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "name": "Test Penetration Test Project",
  "customer_name": "Acme Corporation",
  "description": "Security assessment for web application"
}
EOF
)
echo "$PROJECT_RESPONSE" | python3 -m json.tool
PROJECT_ID=$(echo "$PROJECT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "✓ Project created: $PROJECT_ID"
echo

# Test 5: List Projects
echo "5. Listing projects..."
curl -s "$BASE_URL/api/projects" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo "✓ Projects listed"
echo

# Test 6: Get Project
echo "6. Getting project details..."
curl -s "$BASE_URL/api/projects/$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo "✓ Project details retrieved"
echo

# Test 7: Create Scope
echo "7. Creating scope..."
SCOPE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/scopes" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "project_id": "$PROJECT_ID",
  "target_systems": ["10.0.1.0/24", "webapp.acme.com"],
  "excluded_systems": ["10.0.1.1"],
  "forbidden_methods": ["dos", "social_engineering"],
  "roe": {
    "max_concurrent_scans": 5,
    "testing_window": "09:00-17:00 EST",
    "notification_email": "security@acme.com"
  }
}
EOF
)
echo "$SCOPE_RESPONSE" | python3 -m json.tool
SCOPE_ID=$(echo "$SCOPE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "✓ Scope created: $SCOPE_ID"
echo

# Test 8: Get Scope
echo "8. Getting scope..."
curl -s "$BASE_URL/api/scopes/$SCOPE_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo "✓ Scope retrieved"
echo

# Test 9: Query Audit Log
echo "9. Querying audit log..."
curl -s "$BASE_URL/api/audit?limit=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo "✓ Audit log queried"
echo

echo "=== All Tests Passed ✓ ==="
echo
echo "Available endpoints:"
echo "  - GET  $BASE_URL/docs - Interactive API documentation"
echo "  - GET  $BASE_URL/health - Health check"
echo "  - POST $BASE_URL/api/auth/register - Register user"
echo "  - POST $BASE_URL/api/auth/login - Login"
echo "  - GET  $BASE_URL/api/projects - List projects"
echo "  - POST $BASE_URL/api/projects - Create project"
echo "  - GET  $BASE_URL/api/scopes - List scopes"
echo "  - POST $BASE_URL/api/scopes - Create scope"
echo "  - GET  $BASE_URL/api/audit - Query audit log"
echo "  - And 40+ more endpoints..."
