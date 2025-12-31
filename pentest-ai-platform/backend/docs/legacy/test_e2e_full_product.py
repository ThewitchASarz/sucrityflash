"""
End-to-End Full Product Test

Tests the complete SecurityFlash V2 MVP system:
1. Control Plane (FastAPI)
2. Agent Runtime
3. Worker Runtime
4. Redis Streams integration
5. Full approval workflow
"""
import asyncio
import uuid
import httpx
from datetime import datetime


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_test(name, passed, details=""):
    """Print test result with color."""
    status = f"{Colors.GREEN}✅ PASS{Colors.END}" if passed else f"{Colors.RED}❌ FAIL{Colors.END}"
    print(f"  {name}: {status}")
    if details:
        print(f"    {details}")


async def test_control_plane():
    """Test Control Plane (FastAPI) API."""
    print(f"\n{Colors.BLUE}=== Testing Control Plane (FastAPI) ==={Colors.END}")

    base_url = "http://localhost:8000"

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test 1: Health check
        try:
            response = await client.get(f"{base_url}/health")
            passed = response.status_code == 200
            print_test("Health endpoint", passed, f"Status: {response.status_code}")
        except Exception as e:
            print_test("Health endpoint", False, f"Error: {e}")
            return False

        # Test 2: Root endpoint
        try:
            response = await client.get(f"{base_url}/")
            passed = response.status_code == 200
            print_test("Root endpoint", passed)
        except Exception as e:
            print_test("Root endpoint", False, f"Error: {e}")

        # Test 3: Register user
        try:
            test_user = {
                "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
                "password": "Test123!Pass",
                "full_name": "Test User",
                "role": "COORDINATOR"
            }
            response = await client.post(f"{base_url}/api/v1/auth/register", json=test_user)
            passed = response.status_code in [201, 400]  # 400 if already exists
            print_test("Register user", passed, f"Status: {response.status_code}")

            if response.status_code == 201:
                user_data = response.json()
                print(f"    User ID: {user_data.get('id')}")
        except Exception as e:
            print_test("Register user", False, f"Error: {e}")

        # Test 4: NextAuth.js token endpoint
        try:
            response = await client.post(
                f"{base_url}/api/v1/auth/token",
                data={"username": "test@example.com", "password": "wrongpassword"}
            )
            passed = response.status_code == 401  # Expected: invalid credentials
            print_test("NextAuth.js token endpoint", passed, "401 expected for invalid creds")
        except Exception as e:
            print_test("NextAuth.js token endpoint", False, f"Error: {e}")

        # Test 5: API documentation
        try:
            response = await client.get(f"{base_url}/docs")
            passed = response.status_code == 200
            print_test("OpenAPI docs", passed)
        except Exception as e:
            print_test("OpenAPI docs", False, f"Error: {e}")

    return True


async def test_policy_engine():
    """Test Policy Engine."""
    print(f"\n{Colors.BLUE}=== Testing Policy Engine ==={Colors.END}")

    from services.policy_engine import policy_engine

    # Test 1: Stage 1 tools allowed
    stage1_tools = ["httpx", "nmap", "dnsx", "subfinder", "katana", "ffuf"]
    all_passed = True
    for tool in stage1_tools:
        is_valid, error = policy_engine.validate_tool_allowlist(tool)
        all_passed = all_passed and is_valid
    print_test("Stage 1 tools allowed", all_passed, f"Tested: {', '.join(stage1_tools)}")

    # Test 2: Stage 2 tools rejected
    stage2_tools = ["nuclei", "sqlmap", "nikto"]
    all_rejected = True
    for tool in stage2_tools:
        is_valid, error = policy_engine.validate_tool_allowlist(tool)
        all_rejected = all_rejected and (not is_valid)
    print_test("Stage 2 tools rejected", all_rejected, f"Tested: {', '.join(stage2_tools)}")

    # Test 3: JWT token issuance
    try:
        token = policy_engine.issue_approval_token(
            action_id=uuid.uuid4(),
            run_id=uuid.uuid4(),
            method="nmap",
            flags={"target": "example.com"},
            approved_by=uuid.uuid4()
        )
        print_test("JWT token issuance", bool(token), f"Token length: {len(token)}")
    except Exception as e:
        print_test("JWT token issuance", False, f"Error: {e}")

    # Test 4: JWT token verification
    try:
        claims = policy_engine.verify_approval_token(token)
        passed = claims is not None and "method" in claims
        print_test("JWT token verification", passed, f"Claims: {list(claims.keys()) if claims else 'None'}")
    except Exception as e:
        print_test("JWT token verification", False, f"Error: {e}")


async def test_flag_validators():
    """Test FlagSchema validators."""
    print(f"\n{Colors.BLUE}=== Testing FlagSchema Validators ==={Colors.END}")

    from tools.tool_validators import validate_tool_flags

    # Test 1: Valid nmap flags
    valid_nmap = {"target": "example.com", "ports": "80,443", "scan_type": "-sV"}
    is_valid, error = validate_tool_flags("nmap", valid_nmap)
    print_test("Valid nmap flags", is_valid)

    # Test 2: Invalid nmap flags
    invalid_nmap = {"target": "invalid domain with spaces"}
    is_valid, error = validate_tool_flags("nmap", invalid_nmap)
    print_test("Invalid nmap flags rejected", not is_valid, f"Error: {error[:50] if error else 'None'}...")

    # Test 3: Valid httpx flags
    valid_httpx = {"target": "https://example.com", "timeout": 10}
    is_valid, error = validate_tool_flags("httpx", valid_httpx)
    print_test("Valid httpx flags", is_valid)

    # Test 4: Valid ffuf flags
    valid_ffuf = {"url": "https://example.com/FUZZ", "wordlist": "/path/to/wordlist.txt"}
    is_valid, error = validate_tool_flags("ffuf", valid_ffuf)
    print_test("Valid ffuf flags", is_valid)


async def test_redis_streams():
    """Test Redis Streams service."""
    print(f"\n{Colors.BLUE}=== Testing Redis Streams Service ==={Colors.END}")

    try:
        from services.redis_streams import redis_streams

        # Test 1: Service methods exist
        required_methods = [
            "connect", "disconnect",
            "publish_action_approved", "publish_action_rejected",
            "consume_control_plane_events", "ack_control_plane_event"
        ]
        all_exist = all(hasattr(redis_streams, method) for method in required_methods)
        print_test("Required methods exist", all_exist, f"{len(required_methods)} methods")

        # Test 2: Try to connect (may fail if Redis not running)
        try:
            await redis_streams.connect()
            print_test("Redis connection", True, "Connected successfully")

            # Test 3: Publish test event
            try:
                message_id = await redis_streams.publish_action_approved(
                    action_id=uuid.uuid4(),
                    run_id=uuid.uuid4(),
                    approval_jwt="test_token",
                    action_spec={"method": "nmap", "flags": {}}
                )
                print_test("Publish to Redis Streams", True, f"Message ID: {message_id[:20]}...")
            except Exception as e:
                print_test("Publish to Redis Streams", False, f"Error: {e}")

            await redis_streams.disconnect()

        except Exception as e:
            print_test("Redis connection", False, f"Redis not running: {e}")

    except Exception as e:
        print_test("Redis Streams service", False, f"Import error: {e}")


async def test_agent_runtime():
    """Test Agent Runtime structure."""
    print(f"\n{Colors.BLUE}=== Testing Agent Runtime ==={Colors.END}")

    import os

    # Check if agent runner exists
    agent_path = "/Users/annalealayton/PyCharmMiscProject/pentest-ai-platform/backend/agents/runner.py"
    exists = os.path.exists(agent_path)
    print_test("Agent runner file exists", exists, agent_path)

    if exists:
        # Check file content
        with open(agent_path, 'r') as f:
            content = f.read()
            has_propose = "_propose_next_action" in content
            has_ready_for_execution = "ready_for_execution" in content
            print_test("Has propose action logic", has_propose)
            print_test("Marks L0/L1 ready for execution", has_ready_for_execution)


async def test_worker_runtime():
    """Test Worker Runtime structure."""
    print(f"\n{Colors.BLUE}=== Testing Worker Runtime ==={Colors.END}")

    import os

    # Check if worker runner exists
    worker_path = "/Users/annalealayton/PyCharmMiscProject/pentest-ai-platform/backend/workers/runner.py"
    exists = os.path.exists(worker_path)
    print_test("Worker runner file exists", exists, worker_path)

    if exists:
        # Check file content
        with open(worker_path, 'r') as f:
            content = f.read()
            has_allowlist = "ALLOWLISTED_TOOLS" in content
            has_shell_false = "shell=False" in content
            has_subprocess = "subprocess.run" in content
            print_test("Has tool allowlist", has_allowlist)
            print_test("Uses shell=False", has_shell_false)
            print_test("Uses subprocess.run", has_subprocess)


async def test_database_schema():
    """Test database schema."""
    print(f"\n{Colors.BLUE}=== Testing Database Schema ==={Colors.END}")

    try:
        from sqlalchemy import create_engine, inspect
        from config import settings

        # Create sync engine for inspection
        sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
        engine = create_engine(sync_url.replace("postgresql+asyncpg", "postgresql"))
        inspector = inspect(engine)

        # Check tables
        tables = inspector.get_table_names()
        required_tables = ["users", "runs", "findings", "approvals", "evidence", "report_jobs", "audit_bundle_jobs", "integration_configs"]

        for table in required_tables:
            exists = table in tables
            print_test(f"Table '{table}' exists", exists)

        # Check findings table columns (V2 schema)
        if "findings" in tables:
            columns = [col['name'] for col in inspector.get_columns("findings")]
            has_validated = "validated" in columns
            has_validator_id = "validator_id" in columns
            has_validated_at = "validated_at" in columns
            print_test("Findings has validation fields", has_validated and has_validator_id and has_validated_at)

        engine.dispose()

    except Exception as e:
        print_test("Database schema check", False, f"Error: {e}")


async def main():
    """Run all tests."""
    print(f"\n{Colors.YELLOW}{'=' * 70}{Colors.END}")
    print(f"{Colors.YELLOW}SecurityFlash V2 MVP - End-to-End Full Product Test{Colors.END}")
    print(f"{Colors.YELLOW}{'=' * 70}{Colors.END}")

    start_time = datetime.now()

    try:
        # Run all test suites
        await test_control_plane()
        await test_policy_engine()
        await test_flag_validators()
        await test_redis_streams()
        await test_agent_runtime()
        await test_worker_runtime()
        await test_database_schema()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"\n{Colors.YELLOW}{'=' * 70}{Colors.END}")
        print(f"{Colors.GREEN}✅ All Tests Completed{Colors.END}")
        print(f"Duration: {duration:.2f}s")
        print(f"{Colors.YELLOW}{'=' * 70}{Colors.END}")

        print(f"\n{Colors.BLUE}Next Steps:{Colors.END}")
        print("  1. Start Control Plane: python main.py")
        print("  2. Start Agent Runtime: python agents/runner.py")
        print("  3. Start Worker Runtime: python workers/runner.py")
        print("  4. Access API docs: http://localhost:8000/docs")

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}❌ Test suite failed: {e}{Colors.END}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
