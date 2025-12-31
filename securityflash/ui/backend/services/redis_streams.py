"""
Redis Streams event bus service (V2 PRIMARY requirement).

Per spec: "Redis Streams is the PRIMARY event bus. NOT database polling.
Use Consumer Groups (XGROUP CREATE, XREADGROUP, XCLAIM for restart-safe recovery)."
"""
import redis.asyncio as aioredis
from typing import Optional, List, Dict, Any
import json
import uuid
from datetime import datetime

from config import settings


class RedisStreamsService:
    """
    Redis Streams event bus with Consumer Groups.

    Stream Structure:
    - control_plane_events: Control Plane publishes ActionSpecs here
    - agent_events: Agent Runtime publishes reasoning results here
    - worker_events: Worker Runtime publishes execution results here

    Consumer Groups:
    - agent_group: Agent Runtime consumes from control_plane_events
    - worker_group: Worker Runtime consumes from agent_events
    - control_plane_group: Control Plane consumes from worker_events
    """

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.stream_control_plane = "control_plane_events"
        self.stream_agent = "agent_events"
        self.stream_worker = "worker_events"

    async def connect(self):
        """Connect to Redis and initialize streams/groups."""
        if not self.redis:
            self.redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )

            # Initialize streams and consumer groups (idempotent)
            await self._init_stream_and_group(self.stream_control_plane, "agent_group")
            await self._init_stream_and_group(self.stream_agent, "worker_group")
            await self._init_stream_and_group(self.stream_worker, "control_plane_group")

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            self.redis = None

    async def _init_stream_and_group(self, stream_name: str, group_name: str):
        """Initialize stream and consumer group (idempotent)."""
        try:
            # Create consumer group (MKSTREAM creates stream if not exists)
            await self.redis.xgroup_create(
                name=stream_name,
                groupname=group_name,
                id="0",
                mkstream=True
            )
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                # BUSYGROUP means group already exists (expected)
                raise

    # ===== Control Plane Publishing =====

    async def publish_action_approved(
        self,
        action_id: uuid.UUID,
        run_id: uuid.UUID,
        approval_jwt: str,
        action_spec: Dict[str, Any]
    ) -> str:
        """
        Publish action approval event to control_plane_events stream.

        Args:
            action_id: Action ID
            run_id: Run ID
            approval_jwt: JWT approval token from Policy Engine
            action_spec: Full ActionSpec with tool, method, flags

        Returns:
            str: Redis message ID
        """
        event = {
            "event_type": "action_approved",
            "action_id": str(action_id),
            "run_id": str(run_id),
            "approval_jwt": approval_jwt,
            "action_spec": json.dumps(action_spec),
            "timestamp": datetime.utcnow().isoformat()
        }

        message_id = await self.redis.xadd(
            self.stream_control_plane,
            event
        )

        return message_id

    async def publish_action_rejected(
        self,
        action_id: uuid.UUID,
        run_id: uuid.UUID,
        reason: str
    ) -> str:
        """Publish action rejection event."""
        event = {
            "event_type": "action_rejected",
            "action_id": str(action_id),
            "run_id": str(run_id),
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }

        message_id = await self.redis.xadd(
            self.stream_control_plane,
            event
        )

        return message_id

    # ===== Agent Runtime Consuming =====

    async def consume_control_plane_events(
        self,
        consumer_name: str,
        count: int = 10,
        block_ms: int = 5000
    ) -> List[tuple]:
        """
        Consume events from control_plane_events stream (Agent Runtime).

        Uses XREADGROUP for Consumer Group semantics (restart-safe).

        Args:
            consumer_name: Unique consumer name (e.g., "agent-worker-1")
            count: Max messages to read
            block_ms: Block timeout in milliseconds

        Returns:
            List of (message_id, data) tuples
        """
        result = await self.redis.xreadgroup(
            groupname="agent_group",
            consumername=consumer_name,
            streams={self.stream_control_plane: ">"},
            count=count,
            block=block_ms
        )

        messages = []
        if result:
            for stream_name, stream_messages in result:
                for message_id, data in stream_messages:
                    messages.append((message_id, data))

        return messages

    async def ack_control_plane_event(self, message_id: str):
        """Acknowledge processed message from control_plane_events."""
        await self.redis.xack(
            self.stream_control_plane,
            "agent_group",
            message_id
        )

    # ===== Worker Runtime Consuming =====

    async def consume_agent_events(
        self,
        consumer_name: str,
        count: int = 10,
        block_ms: int = 5000
    ) -> List[tuple]:
        """
        Consume events from agent_events stream (Worker Runtime).

        Uses XREADGROUP for Consumer Group semantics.

        Args:
            consumer_name: Unique consumer name (e.g., "worker-1")
            count: Max messages to read
            block_ms: Block timeout in milliseconds

        Returns:
            List of (message_id, data) tuples
        """
        result = await self.redis.xreadgroup(
            groupname="worker_group",
            consumername=consumer_name,
            streams={self.stream_agent: ">"},
            count=count,
            block=block_ms
        )

        messages = []
        if result:
            for stream_name, stream_messages in result:
                for message_id, data in stream_messages:
                    messages.append((message_id, data))

        return messages

    async def ack_agent_event(self, message_id: str):
        """Acknowledge processed message from agent_events."""
        await self.redis.xack(
            self.stream_agent,
            "worker_group",
            message_id
        )

    # ===== Agent Runtime Publishing =====

    async def publish_agent_reasoning_complete(
        self,
        action_id: uuid.UUID,
        run_id: uuid.UUID,
        reasoning: Dict[str, Any]
    ) -> str:
        """Publish agent reasoning result to agent_events stream."""
        event = {
            "event_type": "agent_reasoning_complete",
            "action_id": str(action_id),
            "run_id": str(run_id),
            "reasoning": json.dumps(reasoning),
            "timestamp": datetime.utcnow().isoformat()
        }

        message_id = await self.redis.xadd(
            self.stream_agent,
            event
        )

        return message_id

    # ===== Worker Runtime Publishing =====

    async def publish_worker_execution_complete(
        self,
        action_id: uuid.UUID,
        run_id: uuid.UUID,
        execution_result: Dict[str, Any]
    ) -> str:
        """Publish worker execution result to worker_events stream."""
        event = {
            "event_type": "worker_execution_complete",
            "action_id": str(action_id),
            "run_id": str(run_id),
            "execution_result": json.dumps(execution_result),
            "timestamp": datetime.utcnow().isoformat()
        }

        message_id = await self.redis.xadd(
            self.stream_worker,
            event
        )

        return message_id

    # ===== Control Plane Consuming =====

    async def consume_worker_events(
        self,
        consumer_name: str,
        count: int = 10,
        block_ms: int = 5000
    ) -> List[tuple]:
        """
        Consume events from worker_events stream (Control Plane).

        Uses XREADGROUP for Consumer Group semantics.
        """
        result = await self.redis.xreadgroup(
            groupname="control_plane_group",
            consumername=consumer_name,
            streams={self.stream_worker: ">"},
            count=count,
            block=block_ms
        )

        messages = []
        if result:
            for stream_name, stream_messages in result:
                for message_id, data in stream_messages:
                    messages.append((message_id, data))

        return messages

    async def ack_worker_event(self, message_id: str):
        """Acknowledge processed message from worker_events."""
        await self.redis.xack(
            self.stream_worker,
            "control_plane_group",
            message_id
        )

    # ===== XCLAIM for restart recovery =====

    async def claim_pending_messages(
        self,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        min_idle_time_ms: int = 60000
    ) -> List[tuple]:
        """
        Claim pending messages from failed consumers using XCLAIM.

        Used for restart-safe recovery per V2 spec.

        Args:
            stream_name: Stream name
            group_name: Consumer group name
            consumer_name: This consumer's name
            min_idle_time_ms: Min idle time before claiming (default: 60s)

        Returns:
            List of (message_id, data) tuples
        """
        # Get pending messages info
        pending = await self.redis.xpending_range(
            name=stream_name,
            groupname=group_name,
            min="-",
            max="+",
            count=100
        )

        claimed_messages = []

        for item in pending:
            message_id = item["message_id"]
            idle_time = item["time_since_delivered"]

            if idle_time >= min_idle_time_ms:
                # Claim this message for current consumer
                result = await self.redis.xclaim(
                    name=stream_name,
                    groupname=group_name,
                    consumername=consumer_name,
                    min_idle_time=min_idle_time_ms,
                    message_ids=[message_id]
                )

                if result:
                    for msg_id, data in result:
                        claimed_messages.append((msg_id, data))

        return claimed_messages


# Global instance
redis_streams = RedisStreamsService()
