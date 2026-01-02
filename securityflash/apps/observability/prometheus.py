"""
Lightweight Prometheus text-format exporter.

This module implements a minimal subset of the Prometheus Python client
required for SecurityFlash observability without adding external dependencies.
Supported metric types:
- Counter
- Gauge
- Histogram
"""
from __future__ import annotations

import copy
import threading
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"


def _format_labels(label_names: Sequence[str], label_values: Sequence[str]) -> str:
    if not label_names:
        return ""
    pairs = [f'{name}="{value}"' for name, value in zip(label_names, label_values)]
    return "{" + ",".join(pairs) + "}"


class MetricRegistry:
    """Registry for all metrics in the current process."""

    def __init__(self) -> None:
        self._metrics: List["BaseMetric"] = []
        self._lock = threading.Lock()

    @property
    def metrics(self) -> List["BaseMetric"]:
        return self._metrics

    def register(self, metric: "BaseMetric") -> None:
        with self._lock:
            self._metrics.append(metric)


REGISTRY = MetricRegistry()


class BaseMetric:
    """Base class for metrics."""

    def __init__(
        self,
        name: str,
        description: str = "",
        labelnames: Optional[Iterable[str]] = None,
        registry: Optional[MetricRegistry] = None,
    ) -> None:
        self.name = name
        self.description = description
        self.labelnames = tuple(labelnames or [])
        self.registry = registry or REGISTRY
        self.registry.register(self)
        self._lock = threading.Lock()

    def labels(self, **label_kwargs: str):
        raise NotImplementedError

    def render(self) -> List[str]:
        raise NotImplementedError


class Counter(BaseMetric):
    """Monotonic increasing counter."""

    def __init__(
        self,
        name: str,
        description: str = "",
        labelnames: Optional[Iterable[str]] = None,
        registry: Optional[MetricRegistry] = None,
    ) -> None:
        super().__init__(name, description, labelnames, registry)
        self._values: Dict[Tuple[str, ...], float] = {}

    def labels(self, **label_kwargs: str):
        key = tuple(label_kwargs.get(label, "") for label in self.labelnames)
        with self._lock:
            self._values.setdefault(key, 0.0)
        return _CounterChild(self, key)

    def inc(self, amount: float = 1.0) -> None:
        self.labels().inc(amount)

    def render(self) -> List[str]:
        lines = [f"# HELP {self.name} {self.description}", f"# TYPE {self.name} counter"]
        with self._lock:
            items = list(self._values.items())
        for key, value in items:
            labels = _format_labels(self.labelnames, key)
            lines.append(f"{self.name}{labels} {float(value)}")
        return lines


class _CounterChild:
    def __init__(self, parent: Counter, key: Tuple[str, ...]) -> None:
        self.parent = parent
        self.key = key

    def inc(self, amount: float = 1.0) -> None:
        with self.parent._lock:
            self.parent._values[self.key] = self.parent._values.get(self.key, 0.0) + amount


class Gauge(BaseMetric):
    """Gauge metric."""

    def __init__(
        self,
        name: str,
        description: str = "",
        labelnames: Optional[Iterable[str]] = None,
        registry: Optional[MetricRegistry] = None,
    ) -> None:
        super().__init__(name, description, labelnames, registry)
        self._values: Dict[Tuple[str, ...], float] = {}

    def labels(self, **label_kwargs: str):
        key = tuple(label_kwargs.get(label, "") for label in self.labelnames)
        with self._lock:
            self._values.setdefault(key, 0.0)
        return _GaugeChild(self, key)

    def set(self, value: float) -> None:
        self.labels().set(value)

    def inc(self, amount: float = 1.0) -> None:
        self.labels().inc(amount)

    def dec(self, amount: float = 1.0) -> None:
        self.labels().dec(amount)

    def render(self) -> List[str]:
        lines = [f"# HELP {self.name} {self.description}", f"# TYPE {self.name} gauge"]
        with self._lock:
            items = list(self._values.items())
        for key, value in items:
            labels = _format_labels(self.labelnames, key)
            lines.append(f"{self.name}{labels} {float(value)}")
        return lines


class _GaugeChild:
    def __init__(self, parent: Gauge, key: Tuple[str, ...]) -> None:
        self.parent = parent
        self.key = key

    def set(self, value: float) -> None:
        with self.parent._lock:
            self.parent._values[self.key] = float(value)

    def inc(self, amount: float = 1.0) -> None:
        with self.parent._lock:
            self.parent._values[self.key] = self.parent._values.get(self.key, 0.0) + amount

    def dec(self, amount: float = 1.0) -> None:
        with self.parent._lock:
            self.parent._values[self.key] = self.parent._values.get(self.key, 0.0) - amount


class Histogram(BaseMetric):
    """Histogram metric."""

    def __init__(
        self,
        name: str,
        description: str = "",
        buckets: Optional[Iterable[float]] = None,
        labelnames: Optional[Iterable[str]] = None,
        registry: Optional[MetricRegistry] = None,
    ) -> None:
        super().__init__(name, description, labelnames, registry)
        self.buckets = tuple(sorted(buckets or (0.1, 0.5, 1, 2.5, 5, 10, 30, 60)))
        self._values: Dict[Tuple[str, ...], Dict[str, float]] = {}

    def labels(self, **label_kwargs: str):
        key = tuple(label_kwargs.get(label, "") for label in self.labelnames)
        with self._lock:
            if key not in self._values:
                self._values[key] = {
                    "buckets": {str(bound): 0 for bound in self.buckets},
                    "+Inf": 0,
                    "sum": 0.0,
                    "count": 0,
                }
        return _HistogramChild(self, key)

    def observe(self, amount: float) -> None:
        self.labels().observe(amount)

    def render(self) -> List[str]:
        lines = [f"# HELP {self.name} {self.description}", f"# TYPE {self.name} histogram"]
        with self._lock:
            snapshot = copy.deepcopy(self._values)
        for key, data in snapshot.items():
            buckets = data["buckets"]
            for bound in self.buckets:
                labels = _format_labels(self.labelnames + ("le",), key + (str(bound),))
                lines.append(f"{self.name}_bucket{labels} {float(buckets.get(str(bound), 0))}")
            labels_inf = _format_labels(self.labelnames + ("le",), key + ("+Inf",))
            lines.append(f"{self.name}_bucket{labels_inf} {float(data.get('+Inf', 0))}")

            labels = _format_labels(self.labelnames, key)
            lines.append(f"{self.name}_sum{labels} {float(data.get('sum', 0.0))}")
            lines.append(f"{self.name}_count{labels} {float(data.get('count', 0))}")
        return lines


class _HistogramChild:
    def __init__(self, parent: Histogram, key: Tuple[str, ...]) -> None:
        self.parent = parent
        self.key = key

    def observe(self, amount: float) -> None:
        with self.parent._lock:
            data = self.parent._values[self.key]
            # Bucket counts
            for bound in self.parent.buckets:
                if amount <= bound:
                    data["buckets"][str(bound)] += 1
            data["+Inf"] += 1
            data["sum"] += float(amount)
            data["count"] += 1


def generate_latest(registry: Optional[MetricRegistry] = None) -> bytes:
    """Render all metrics to Prometheus text exposition format."""
    registry = registry or REGISTRY
    lines: List[str] = []
    for metric in registry.metrics:
        lines.extend(metric.render())
    return ("\n".join(lines) + "\n").encode("utf-8")
