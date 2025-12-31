"""
Policy validator: Pre-execution validation against scope and governance rules.
"""
from typing import Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from models.scope import Scope
from models.test_plan import Action
from models.run import Run


class PolicyViolation(Exception):
    """Raised when an action violates policy."""
    pass


class PolicyValidator:
    """Validates actions against scope and governance policies."""

    async def validate_action(
        self,
        db: AsyncSession,
        action: Action,
        scope: Scope,
        run: Run
    ) -> tuple[bool, Optional[str]]:
        """
        Validate action against all policies before execution.

        Args:
            db: Database session
            action: Action to validate
            scope: Locked scope
            run: Active run

        Returns:
            tuple[bool, Optional[str]]: (is_valid, error_message)

        Validation checks:
            1. Scope lock verification
            2. Target in scope
            3. Target not excluded
            4. Method not forbidden
            5. Rate limits (ROE)
            6. Testing window (ROE)
            7. Concurrent action limits (ROE)
        """
        # 1. Verify scope is locked
        if not scope.locked_at:
            return False, "Scope is not locked"

        # 2. Verify target is in scope
        target = action.target
        in_scope = self._check_target_in_scope(target, scope.target_systems)
        if not in_scope:
            return False, f"Target {target} is not in approved scope"

        # 3. Verify target is not excluded
        is_excluded = self._check_target_in_scope(target, scope.excluded_systems)
        if is_excluded:
            return False, f"Target {target} is in excluded systems"

        # 4. Verify method is not forbidden
        if action.method in scope.forbidden_methods:
            return False, f"Method {action.method} is forbidden by scope"

        # 5. Check rate limits (ROE)
        rate_limit_valid, rate_error = await self._check_rate_limits(db, action, scope, run)
        if not rate_limit_valid:
            return False, rate_error

        # 6. Check testing window (ROE)
        window_valid, window_error = self._check_testing_window(scope)
        if not window_valid:
            return False, window_error

        # 7. Check concurrent action limits (ROE)
        concurrent_valid, concurrent_error = await self._check_concurrent_limits(db, scope, run)
        if not concurrent_valid:
            return False, concurrent_error

        return True, None

    def _check_target_in_scope(self, target: str, scope_list: list[str]) -> bool:
        """
        Check if target matches any entry in scope list.

        Supports:
            - Exact match: "192.168.1.10"
            - CIDR range: "192.168.1.0/24"
            - Domain: "example.com"
            - Wildcard subdomain: "*.example.com"
        """
        for scope_entry in scope_list:
            # Exact match
            if target == scope_entry:
                return True

            # Domain/subdomain match
            if scope_entry.startswith("*."):
                domain = scope_entry[2:]
                if target.endswith(domain) or target == domain:
                    return True
            elif scope_entry in target:
                return True

            # CIDR match (simplified - real implementation would use ipaddress module)
            if "/" in scope_entry and target.startswith(scope_entry.split("/")[0][:10]):
                return True

        return False

    async def _check_rate_limits(
        self,
        db: AsyncSession,
        action: Action,
        scope: Scope,
        run: Run
    ) -> tuple[bool, Optional[str]]:
        """
        Check if action respects rate limits defined in ROE.

        ROE example:
        {
            "max_requests_per_minute": 10,
            "max_requests_per_target": 100
        }
        """
        roe = scope.roe
        if not roe:
            return True, None

        max_rpm = roe.get("max_requests_per_minute")
        if max_rpm:
            # Count actions in last minute for this run
            one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
            result = await db.execute(
                select(Action)
                .where(
                    Action.test_plan_id == action.test_plan_id,
                    Action.executed_at >= one_minute_ago,
                    Action.executed_at.isnot(None)
                )
            )
            recent_actions = result.scalars().all()

            if len(recent_actions) >= max_rpm:
                return False, f"Rate limit exceeded: {len(recent_actions)}/{max_rpm} requests per minute"

        return True, None

    def _check_testing_window(self, scope: Scope) -> tuple[bool, Optional[str]]:
        """
        Check if current time is within allowed testing window.

        ROE example:
        {
            "testing_window": {
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "hours": {"start": "09:00", "end": "17:00"},
                "timezone": "America/New_York"
            }
        }
        """
        roe = scope.roe
        if not roe or "testing_window" not in roe:
            return True, None

        window = roe["testing_window"]
        now = datetime.utcnow()

        # Check day of week
        if "days" in window:
            current_day = now.strftime("%A").lower()
            allowed_days = [d.lower() for d in window["days"]]
            if current_day not in allowed_days:
                return False, f"Testing not allowed on {current_day}"

        # Check time window (simplified - real implementation would handle timezones)
        if "hours" in window:
            current_hour = now.hour
            start_hour = int(window["hours"]["start"].split(":")[0])
            end_hour = int(window["hours"]["end"].split(":")[0])

            if not (start_hour <= current_hour < end_hour):
                return False, f"Testing not allowed at {now.strftime('%H:%M')} UTC"

        return True, None

    async def _check_concurrent_limits(
        self,
        db: AsyncSession,
        scope: Scope,
        run: Run
    ) -> tuple[bool, Optional[str]]:
        """
        Check if concurrent action limit is respected.

        ROE example:
        {
            "max_concurrent_actions": 5
        }
        """
        roe = scope.roe
        if not roe:
            return True, None

        max_concurrent = roe.get("max_concurrent_actions")
        if max_concurrent:
            # Count currently executing actions for this run
            result = await db.execute(
                select(Action)
                .join(Action.test_plan)
                .where(
                    Action.status == "executing",
                    Action.test_plan.has(scope_id=scope.id)
                )
            )
            executing_actions = result.scalars().all()

            if len(executing_actions) >= max_concurrent:
                return False, f"Concurrent action limit exceeded: {len(executing_actions)}/{max_concurrent}"

        return True, None


# Global instance
policy_validator = PolicyValidator()
