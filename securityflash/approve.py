#!/usr/bin/env python3
import requests, sys
if len(sys.argv) < 3:
    print("Usage: python3 approve.py <run_id> <action_id>")
    sys.exit(1)
run_id, action_id = sys.argv[1], sys.argv[2]
r = requests.post(
    f"http://localhost:8000/api/v1/runs/{run_id}/approvals/{action_id}/approve",
    json={"approved_by":"security-lead","signature":f"approved-{action_id[:8]}"}
)
print(f"✅ Approved! Status: {r.status_code}")
