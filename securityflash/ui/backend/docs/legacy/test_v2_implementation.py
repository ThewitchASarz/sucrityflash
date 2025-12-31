"""
V2 Implementation Test Script

Tests core V2 components:
1. Policy Engine tool validation
2. FlagSchema validation
3. Tool allowlist enforcement
4. JWT approval token issuance
"""
import asyncio
import uuid
from pydantic import ValidationError

# Test imports
from services.policy_engine import policy_engine
from tools.tool_validators import validate_tool_flags, FLAG_VALIDATORS
from tools.tool_allowlist import AllowedToolV2MVP, validate_tool_allowlist


def test_policy_engine():
    """Test Policy Engine tool validation."""
    print("\n=== Testing Policy Engine ===")

    # Test Stage 1 tools (should pass)
    stage1_tools = ["httpx", "nmap", "dnsx", "subfinder", "katana", "ffuf"]
    for tool in stage1_tools:
        is_valid, error = policy_engine.validate_tool_allowlist(tool)
        status = "✅ PASS" if is_valid else f"❌ FAIL: {error}"
        print(f"  {tool}: {status}")

    # Test Stage 2 tools (should fail)
    print("\n  Testing Stage 2 rejection:")
    stage2_tools = ["nuclei", "sqlmap", "nikto"]
    for tool in stage2_tools:
        is_valid, error = policy_engine.validate_tool_allowlist(tool)
        status = "✅ PASS (rejected)" if not is_valid else "❌ FAIL (should reject)"
        print(f"  {tool}: {status} - {error}")

    # Test unknown tool (should fail)
    print("\n  Testing unknown tool rejection:")
    is_valid, error = policy_engine.validate_tool_allowlist("metasploit")
    status = "✅ PASS (rejected)" if not is_valid else "❌ FAIL (should reject)"
    print(f"  metasploit: {status} - {error}")


def test_flag_validators():
    """Test FlagSchema validators."""
    print("\n=== Testing FlagSchema Validators ===")

    # Test valid nmap flags
    print("\n  Testing nmap validator:")
    valid_nmap = {
        "target": "example.com",
        "ports": "80,443,8000-9000",
        "scan_type": "-sV",
        "timing": "-T4"
    }
    is_valid, error = validate_tool_flags("nmap", valid_nmap)
    print(f"  Valid nmap flags: {'✅ PASS' if is_valid else f'❌ FAIL: {error}'}")

    # Test invalid nmap flags (bad target)
    invalid_nmap = {
        "target": "invalid domain with spaces",
        "ports": "80,443"
    }
    is_valid, error = validate_tool_flags("nmap", invalid_nmap)
    print(f"  Invalid nmap target: {'✅ PASS (rejected)' if not is_valid else '❌ FAIL'} - {error}")

    # Test valid httpx flags
    print("\n  Testing httpx validator:")
    valid_httpx = {
        "target": "https://example.com",
        "follow_redirects": True,
        "timeout": 10
    }
    is_valid, error = validate_tool_flags("httpx", valid_httpx)
    print(f"  Valid httpx flags: {'✅ PASS' if is_valid else f'❌ FAIL: {error}'}")

    # Test valid dnsx flags
    print("\n  Testing dnsx validator:")
    valid_dnsx = {
        "domain": "example.com",
        "record_type": "A"
    }
    is_valid, error = validate_tool_flags("dnsx", valid_dnsx)
    print(f"  Valid dnsx flags: {'✅ PASS' if is_valid else f'❌ FAIL: {error}'}")

    # Test valid subfinder flags
    print("\n  Testing subfinder validator:")
    valid_subfinder = {
        "domain": "example.com",
        "timeout": 30
    }
    is_valid, error = validate_tool_flags("subfinder", valid_subfinder)
    print(f"  Valid subfinder flags: {'✅ PASS' if is_valid else f'❌ FAIL: {error}'}")

    # Test valid katana flags
    print("\n  Testing katana validator:")
    valid_katana = {
        "url": "https://example.com",
        "depth": 2,
        "timeout": 60
    }
    is_valid, error = validate_tool_flags("katana", valid_katana)
    print(f"  Valid katana flags: {'✅ PASS' if is_valid else f'❌ FAIL: {error}'}")

    # Test valid ffuf flags
    print("\n  Testing ffuf validator:")
    valid_ffuf = {
        "url": "https://example.com/FUZZ",
        "wordlist": "/usr/share/wordlists/common.txt",
        "threads": 10
    }
    is_valid, error = validate_tool_flags("ffuf", valid_ffuf)
    print(f"  Valid ffuf flags: {'✅ PASS' if is_valid else f'❌ FAIL: {error}'}")


def test_tool_allowlist():
    """Test tool allowlist enum."""
    print("\n=== Testing Tool Allowlist Enum ===")

    # Test allowed tools
    print("\n  Allowed Stage 1 tools:")
    for tool in AllowedToolV2MVP.get_allowed_tools():
        is_allowed = AllowedToolV2MVP.is_allowed(tool)
        print(f"  {tool}: {'✅ PASS' if is_allowed else '❌ FAIL'}")

    # Test rejected tools
    print("\n  Rejected tools:")
    rejected = ["nuclei", "sqlmap", "nikto", "burpsuite", "metasploit"]
    for tool in rejected:
        is_allowed = AllowedToolV2MVP.is_allowed(tool)
        print(f"  {tool}: {'✅ PASS (rejected)' if not is_allowed else '❌ FAIL'}")


def test_jwt_approval_token():
    """Test JWT approval token issuance."""
    print("\n=== Testing JWT Approval Token ===")

    # Issue token
    action_id = uuid.uuid4()
    run_id = uuid.uuid4()
    user_id = uuid.uuid4()

    token = policy_engine.issue_approval_token(
        action_id=action_id,
        run_id=run_id,
        method="nmap",
        flags={"target": "example.com", "ports": "80,443"},
        approved_by=user_id,
        ttl_minutes=30
    )

    print(f"  Token issued: ✅ PASS")
    print(f"  Token (truncated): {token[:50]}...")

    # Verify token
    claims = policy_engine.verify_approval_token(token)
    if claims:
        print(f"  Token verified: ✅ PASS")
        print(f"    - action_id: {claims['sub']}")
        print(f"    - run_id: {claims['run_id']}")
        print(f"    - method: {claims['method']}")
        print(f"    - flags: {claims['flags']}")
        print(f"    - approved_by: {claims['approved_by']}")
    else:
        print(f"  Token verified: ❌ FAIL")

    # Test invalid token
    invalid_token = "invalid.jwt.token"
    claims = policy_engine.verify_approval_token(invalid_token)
    print(f"  Invalid token rejected: {'✅ PASS' if claims is None else '❌ FAIL'}")


def test_action_spec_validation():
    """Test ActionSpec validation."""
    print("\n=== Testing ActionSpec Validation ===")

    # Valid ActionSpec
    valid_spec = {
        "action_id": str(uuid.uuid4()),
        "run_id": str(uuid.uuid4()),
        "method": "nmap",
        "flags": {"target": "example.com", "ports": "80,443"}
    }
    is_valid, error = policy_engine.validate_action_spec(valid_spec)
    print(f"  Valid ActionSpec: {'✅ PASS' if is_valid else f'❌ FAIL: {error}'}")

    # Invalid ActionSpec (missing field)
    invalid_spec = {
        "action_id": str(uuid.uuid4()),
        "method": "nmap"
    }
    is_valid, error = policy_engine.validate_action_spec(invalid_spec)
    print(f"  Missing field rejected: {'✅ PASS (rejected)' if not is_valid else '❌ FAIL'} - {error}")

    # Invalid ActionSpec (Stage 2 tool)
    stage2_spec = {
        "action_id": str(uuid.uuid4()),
        "run_id": str(uuid.uuid4()),
        "method": "nuclei",
        "flags": {}
    }
    is_valid, error = policy_engine.validate_action_spec(stage2_spec)
    print(f"  Stage 2 tool rejected: {'✅ PASS (rejected)' if not is_valid else '❌ FAIL'} - {error}")


def main():
    """Run all tests."""
    print("=" * 70)
    print("V2 IMPLEMENTATION TEST SUITE")
    print("=" * 70)

    try:
        test_policy_engine()
        test_flag_validators()
        test_tool_allowlist()
        test_jwt_approval_token()
        test_action_spec_validation()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
