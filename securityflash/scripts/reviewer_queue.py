"""
SecurityFlash V1 Reviewer CLI Interface.

MUST-FIX E: Human Interface for Approvals.

This script provides a command-line interface for human reviewers
to approve or reject pending ActionSpecs.

Usage:
    python scripts/reviewer_queue.py --queue --run-id <run_id>
    python scripts/reviewer_queue.py --approve <action_id> --run-id <run_id>
    python scripts/reviewer_queue.py --reject <action_id> --run-id <run_id>

Examples:
    # List all pending approvals
    python scripts/reviewer_queue.py --queue --run-id abc123

    # Approve a specific action
    python scripts/reviewer_queue.py --approve def456 --run-id abc123

    # Reject a specific action
    python scripts/reviewer_queue.py --reject def456 --run-id abc123

The script communicates with the Control Plane API:
- GET  /api/v1/runs/{run_id}/approvals/pending
- POST /api/v1/runs/{run_id}/approvals/{action_id}/approve
- POST /api/v1/runs/{run_id}/approvals/{action_id}/reject

V1 Requirements:
- Display: action_id, tool, target, risk_score, approval_tier
- Approve: issues JWT token, updates status to APPROVED
- Reject: updates status to REJECTED (terminal state)

Alternative: Use Postman collection (included in docs/)
"""
import click
import requests
from tabulate import tabulate


BASE_URL = "http://localhost:8000/api/v1"


@click.group()
def cli():
    """SecurityFlash Reviewer CLI - MUST-FIX E Human Interface."""
    pass


@cli.command()
@click.option("--run-id", required=True, help="Run ID to query")
def queue(run_id):
    """Show pending approvals for a run."""
    try:
        response = requests.get(f"{BASE_URL}/runs/{run_id}/approvals/pending")

        if response.status_code != 200:
            click.echo(f"❌ Error: {response.status_code} - {response.text}", err=True)
            return

        pending = response.json()

        if not pending:
            click.echo("✅ No pending approvals")
            return

        # Format as table
        table_data = []
        for action in pending:
            table_data.append([
                action["action_id"][:8] + "...",
                action["tool"],
                action["target"],
                f"{action['risk_score']:.2f}",
                action["approval_tier"],
                action["proposed_by"],
                action.get("justification", "")[:40]
            ])

        headers = ["Action ID", "Tool", "Target", "Risk", "Tier", "Proposed By", "Justification"]
        click.echo("\n📋 Pending Approvals:\n")
        click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
        click.echo(f"\nTotal: {len(pending)} pending\n")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.option("--action-id", required=True, help="Action ID to approve")
@click.option("--run-id", required=True, help="Run ID")
@click.option("--reason", default="Approved by reviewer", help="Approval reason")
@click.option("--approved-by", default="reviewer-cli", help="Reviewer ID")
def approve(action_id, run_id, reason, approved_by):
    """Approve an action."""
    try:
        payload = {
            "approved_by": approved_by,
            "reason": reason,
            "signature": f"cli-approval-{action_id[:8]}"
        }

        response = requests.post(
            f"{BASE_URL}/runs/{run_id}/approvals/{action_id}/approve",
            json=payload
        )

        if response.status_code != 200:
            click.echo(f"❌ Error: {response.status_code} - {response.text}", err=True)
            return

        result = response.json()
        click.echo(f"\n✅ Action {action_id[:8]}... APPROVED")
        click.echo(f"   Status: {result['status']}")
        click.echo(f"   Token issued: {result['approval_token'][:20]}...")
        click.echo(f"   Worker can now execute\n")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.option("--action-id", required=True, help="Action ID to reject")
@click.option("--run-id", required=True, help="Run ID")
@click.option("--reason", default="Rejected by reviewer", help="Rejection reason")
@click.option("--approved-by", default="reviewer-cli", help="Reviewer ID")
def reject(action_id, run_id, reason, approved_by):
    """Reject an action."""
    try:
        payload = {
            "approved_by": approved_by,
            "reason": reason,
            "signature": f"cli-rejection-{action_id[:8]}"
        }

        response = requests.post(
            f"{BASE_URL}/runs/{run_id}/approvals/{action_id}/reject",
            json=payload
        )

        if response.status_code != 200:
            click.echo(f"❌ Error: {response.status_code} - {response.text}", err=True)
            return

        result = response.json()
        click.echo(f"\n❌ Action {action_id[:8]}... REJECTED")
        click.echo(f"   Status: {result['status']}")
        click.echo(f"   Reason: {reason}\n")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


if __name__ == "__main__":
    cli()

