#!/usr/bin/env python3
import requests, json
API = "http://localhost:8000/api/v1"
print("\n🔥 SECURITYFLASH PENTEST STATUS\n")
runs = requests.get(f"{API}/projects/c329ba0e-5a2b-4e56-9d4f-edd6150055fa/runs").json()
for r in [x for x in runs if x['status'] == 'RUNNING']:
    print(f"🔴 RUN {r['id'][:16]}... [{r['status']}]\n")
    approvals = requests.get(f"{API}/runs/{r['id']}/approvals/pending").json()
    if approvals:
        print("⏳ PENDING APPROVALS:")
        for a in approvals:
            print(f"   🔸 {a['tool']} {a['target']} - Risk:{a['risk_score']} Tier:{a['approval_tier']}")
            print(f"      {a['justification']}")
            print(f"      APPROVE: python3 approve.py {r['id']} {a['action_id']}\n")
    else:
        print("✅ No pending approvals\n")
    
    actions = requests.get(f"{API}/action-specs?status=APPROVED").json()
    approved = [x for x in actions if x['run_id']==r['id'] and not x.get('executed_at')]
    if approved:
        print(f"✅ APPROVED ({len(approved)} waiting):")
        for a in approved[:3]:
            print(f"   🔹 {a['action_json']['tool']} → {a['action_json']['target']}")
    
    evidence = requests.get(f"{API}/runs/{r['id']}/evidence").json()
    print(f"\n📊 EVIDENCE: {len(evidence)} records")
    for e in evidence[-3:]:
        err = e.get('metadata',{}).get('stderr','')[:80]
        if err:
            print(f"   ❌ {e['evidence_type']}: {err}")
