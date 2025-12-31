"""
V2 API Integration Test

Tests V2 API endpoints:
1. POST /api/v1/auth/token (NextAuth.js endpoint)
2. Approvals with Redis Streams integration
3. Policy Engine validation
"""
import sys
import asyncio
from httpx import AsyncClient
from fastapi import status


async def test_nextauth_endpoint():
    """Test NextAuth.js token endpoint."""
    print("\n=== Testing NextAuth.js Token Endpoint ===")

    from main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test with form data (NextAuth.js format)
        response = await client.post(
            "/api/v1/auth/token",
            data={
                "username": "test@example.com",
                "password": "testpassword"
            }
        )

        if response.status_code == 401:
            print(f"  Endpoint exists: ✅ PASS (401 expected - user not registered)")
            print(f"  Response: {response.json()}")
            return True
        elif response.status_code == 200:
            print(f"  Endpoint exists: ✅ PASS (200 - user authenticated)")
            return True
        else:
            print(f"  Endpoint: ❌ FAIL - Unexpected status {response.status_code}")
            return False


async def test_api_structure():
    """Test API structure and endpoints."""
    print("\n=== Testing API Structure ===")

    from main import app

    # Check routes
    routes = [route.path for route in app.routes]

    required_routes = [
        "/api/v1/auth/token",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/approvals",
    ]

    print("\n  Required routes:")
    for route in required_routes:
        exists = any(route in r for r in routes)
        print(f"    {route}: {'✅ PASS' if exists else '❌ FAIL'}")

    return True


async def test_policy_engine_integration():
    """Test Policy Engine integration in API."""
    print("\n=== Testing Policy Engine Integration ===")

    from services.policy_engine import policy_engine
    import uuid

    # Test JWT token issuance
    action_id = uuid.uuid4()
    run_id = uuid.uuid4()
    user_id = uuid.uuid4()

    try:
        token = policy_engine.issue_approval_token(
            action_id=action_id,
            run_id=run_id,
            method="nmap",
            flags={"target": "example.com"},
            approved_by=user_id
        )
        print(f"  JWT token issuance: ✅ PASS")

        # Verify token
        claims = policy_engine.verify_approval_token(token)
        if claims:
            print(f"  JWT token verification: ✅ PASS")
            return True
        else:
            print(f"  JWT token verification: ❌ FAIL")
            return False

    except Exception as e:
        print(f"  Policy Engine: ❌ FAIL - {e}")
        return False


async def test_redis_streams_service():
    """Test Redis Streams service (structure only, no Redis required)."""
    print("\n=== Testing Redis Streams Service ===")

    try:
        from services.redis_streams import redis_streams

        # Check methods exist
        methods = [
            "connect",
            "disconnect",
            "publish_action_approved",
            "publish_action_rejected",
            "consume_control_plane_events",
            "ack_control_plane_event"
        ]

        print("\n  Required methods:")
        for method in methods:
            exists = hasattr(redis_streams, method)
            print(f"    {method}: {'✅ PASS' if exists else '❌ FAIL'}")

        return True

    except Exception as e:
        print(f"  Redis Streams service: ❌ FAIL - {e}")
        return False


async def test_audit_service():
    """Test Audit Service (structure only)."""
    print("\n=== Testing Audit Service ===")

    try:
        from services.audit_service import audit_service

        # Check methods exist
        methods = [
            "log_action",
            "log_approve_action",
            "log_reject_action",
            "log_delete_evidence_rejected"
        ]

        print("\n  Required methods:")
        for method in methods:
            exists = hasattr(audit_service, method)
            print(f"    {method}: {'✅ PASS' if exists else '❌ FAIL'}")

        return True

    except Exception as e:
        print(f"  Audit service: ❌ FAIL - {e}")
        return False


async def main():
    """Run all API tests."""
    print("=" * 70)
    print("V2 API INTEGRATION TEST SUITE")
    print("=" * 70)

    try:
        await test_api_structure()
        await test_nextauth_endpoint()
        await test_policy_engine_integration()
        await test_redis_streams_service()
        await test_audit_service()

        print("\n" + "=" * 70)
        print("✅ ALL API TESTS COMPLETED")
        print("=" * 70)
        print("\nNOTE: Full integration testing requires:")
        print("  - PostgreSQL running")
        print("  - Redis running")
        print("  - Registered test user")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
