# V2 Workers Directory

**IMPORTANT**: V2 does NOT execute tools directly.

## Architecture

- **SecurityFlash V1**: Executes all tools, manages evidence, enforces policy
- **Pentest-AI-Platform V2**: Orchestration UI only, delegates to V1

## What Belongs Here

ONLY orchestration logic that:
- Submits action specs to SecurityFlash V1 API
- Monitors run status via V1 API
- Queries results/evidence from V1 API

## What Does NOT Belong Here

- subprocess calls to tools
- Direct tool execution
- Evidence storage
- Approval bypassing
- Policy logic

All execution lives in SecurityFlash V1 Worker Runtime.

## How V2 Interacts with V1

```python
from clients.securityflash_client import get_securityflash_client

client = get_securityflash_client()

# Submit action spec to V1 for execution
result = await client.submit_action_spec(
    run_id=run_id,
    method="nmap",
    args={" target": "192.168.1.1"},
    risk_level="L2"
)

# V1 will:
# 1. Validate against policy
# 2. Request approval if needed
# 3. Execute via Worker Runtime
# 4. Store evidence
# 5. Return results
```

See `clients/securityflash_client.py` for full API.
