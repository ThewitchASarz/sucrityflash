#!/usr/bin/env python3
"""
SecurityFlash Live Pentest Monitor
Real-time dashboard for monitoring agent activity and approving actions
"""
import requests
import json
import time
import os
from datetime import datetime

API_BASE = "http://localhost:8000/api/v1"

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def monitor():
    while True:
        try:
            clear_screen()
            print("=" * 100)
            print("🔥 SECURITYFLASH - LIVE PENTEST MONITOR")
            print("=" * 100)
            print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
            # Get all runs
            projects = requests.get(f"{API_BASE}/projects").json()
            
            for project in projects:
                runs = requests.get(f"{API_BASE}/projects/{project['id']}/runs").json()
                
                for run in runs:
                    if run['status'] in ['RUNNING', 'PENDING']:
                        print(f"🔴 ACTIVE RUN: {run['id']}")
                        print(f"   Project: {project['name']}")
                        print(f"   Status: {run['status']}")
                        print(f"   Started: {run.get('started_at', 'Not started')}")
                        print(f"   Iteration: {run['iteration_count']}/{run['max_iterations']}")
                        print()
                        
                        # PENDING APPROVALS
                        print("⏳ PENDING APPROVALS:")
                        try:
                            approvals = requests.get(f"{API_BASE}/runs/{run['id']}/approvals/pending").json()
                            if approvals:
                                for approval in approvals:
                                    print(f"   🔸 Action: {approval['action_id'][:16]}...")
                                    print(f"      🔧 Tool: {approval['tool']}")
                                    print(f"      🎯 Target: {approval['target']}")
                                    print(f"      ⚙️  Args: {' '.join(approval['arguments'])}")
                                    print(f"      ⚠️  Risk: {approval['risk_score']} (Tier {approval['approval_tier']})")
                                    print(f"      💬 Why: {approval['justification']}")
                                    print(f"      👤 By: {approval['proposed_by']}")
                                    print()
                                    print(f"      ✅ TO APPROVE, RUN:")
                                    print(f"         python3 -c \"import requests; requests.post(")
                                    print(f"           '{API_BASE}/runs/{run['id']}/approvals/{approval['action_id']}/approve',")
                                    print(f"           json={{'approved_by':'security-lead','signature':'approved-{approval['action_id'][:8]}'}})\"")
                                    print()
                            else:
                                print("   ✅ No pending approvals")
                        except:
                            print("   ⚠️  Could not fetch approvals")
                        print()
                        
                        # APPROVED ACTIONS
                        print("✅ APPROVED (waiting for worker):")
                        try:
                            actions = requests.get(f"{API_BASE}/action-specs?status=APPROVED").json()
                            approved_for_run = [a for a in actions if a['run_id'] == run['id'] and not a.get('executed_at')]
                            if approved_for_run:
                                for action in approved_for_run[:5]:
                                    aj = action['action_json']
                                    print(f"   🔹 {aj['tool']} → {aj['target']}")
                                    print(f"      Args: {' '.join(aj['arguments'])}")
                            else:
                                print("   None")
                        except Exception as e:
                            print(f"   ⚠️  Error: {e}")
                        print()
                        
                        # EVIDENCE
                        print("📊 EVIDENCE:")
                        try:
                            evidence = requests.get(f"{API_BASE}/runs/{run['id']}/evidence").json()
                            print(f"   Total records: {len(evidence)}")
                            if evidence:
                                for e in evidence[-5:]:  # Last 5
                                    print(f"   🔸 {e['evidence_type']} by {e['generated_by']}")
                                    if e.get('metadata', {}).get('stderr'):
                                        stderr = e['metadata']['stderr'][:120]
                                        print(f"      ❌ Error: {stderr}")
                                    elif e.get('metadata', {}).get('stdout'):
                                        stdout = e['metadata']['stdout'][:120]
                                        print(f"      ✅ Output: {stdout}")
                        except Exception as e:
                            print(f"   ⚠️  Error: {e}")
                        print()
                        
                        # WORKER STATUS
                        print("🤖 WORKER STATUS:")
                        with open('/tmp/worker.log', 'r') as f:
                            lines = f.readlines()
                            last_lines = [l.strip() for l in lines[-10:] if 'INFO' in l or 'ERROR' in l or 'WARNING' in l]
                            for line in last_lines[-3:]:
                                print(f"   {line}")
                        print()
                        
                        # AGENT STATUS
                        print("🤖 AGENT STATUS:")
                        with open('/tmp/agent.log', 'r') as f:
                            lines = f.readlines()
                            last_lines = [l.strip() for l in lines[-10:] if 'INFO' in l or 'ERROR' in l]
                            for line in last_lines[-3:]:
                                print(f"   {line}")
                        print()
            
            print("=" * 100)
            print("Press Ctrl+C to exit. Refreshing every 5 seconds...")
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\n\n👋 Monitor stopped")
            break
        except Exception as e:
            print(f"\n⚠️  Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor()
