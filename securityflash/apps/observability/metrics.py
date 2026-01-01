"""
Reusable observability primitives for SecurityFlash runtimes.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, Tuple

import redis

from apps.observability.prometheus import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

logger = logging.getLogger(__name__)

# Metric definitions
approval_latency_seconds = Histogram(
    "approval_latency_seconds",
    "Seconds between action proposal and reviewer approval",
    buckets=(5, 15, 30, 60, 120, 300, 600, 900, 1800),
)

worker_errors_total = Counter(
    "worker_errors_total",
    "Total worker execution errors",
    labelnames=("worker",),
)

worker_liveness = Gauge(
    "worker_liveness",
    "Liveness heartbeat set by worker main loop",
    labelnames=("worker",),
)

redis_streams_lag = Gauge(
    "redis_streams_lag",
    "Pending Redis Streams entries per consumer group",
    labelnames=("stream", "group"),
)


def record_approval_latency(proposed_at: datetime) -> None:
    """Record approval latency histogram sample."""
    try:
        latency_sec = (datetime.utcnow() - proposed_at).total_seconds()
        approval_latency_seconds.observe(latency_sec)
    except Exception as exc:  # pragma: no cover - observability only
        logger.debug("Failed to record approval latency: %s", exc, exc_info=True)


def increment_worker_error(worker_name: str) -> None:
    """Increment worker error counter."""
    worker_errors_total.labels(worker=worker_name).inc()


def set_worker_liveness(worker_name: str, alive: bool) -> None:
    """Set worker liveness gauge."""
    worker_liveness.labels(worker=worker_name).set(1 if alive else 0)


def update_redis_streams_lag(
    redis_url: str,
    stream_groups: Iterable[Tuple[str, str]],
    timeout_seconds: float = 2.0,
) -> None:
    """Update Redis Streams lag gauge for each (stream, group) pair."""
    client = redis.Redis.from_url(redis_url, decode_responses=True, socket_timeout=timeout_seconds)
    try:
        for stream, group in stream_groups:
            try:
                pending_info = client.xpending(stream, group)
                pending = pending_info["pending"] if isinstance(pending_info, dict) else 0
                redis_streams_lag.labels(stream=stream, group=group).set(float(pending))
            except Exception as stream_exc:
                logger.debug("Failed to fetch pending messages for %s/%s: %s", stream, group, stream_exc)
                redis_streams_lag.labels(stream=stream, group=group).set(float("nan"))
    finally:
        try:
            client.close()
        except Exception:
            pass
