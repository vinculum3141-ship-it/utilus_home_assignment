"""Monitoring and metrics collection."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SystemHealth:
    """System health status."""

    status: str  # healthy, degraded, unhealthy
    database_connected: bool
    storage_accessible: bool
    last_check: datetime
    details: dict[str, Any] = field(default_factory=dict)

    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        return self.status == "healthy" and self.database_connected


@dataclass
class MetricsCollector:
    """Collects and aggregates metrics."""

    _metrics: dict[str, list[float]] = field(default_factory=dict)

    def record(self, metric_name: str, value: float) -> None:
        """Record a metric value."""
        if metric_name not in self._metrics:
            self._metrics[metric_name] = []
        self._metrics[metric_name].append(value)

    def get_average(self, metric_name: str) -> float:
        """Get average value for a metric."""
        if metric_name not in self._metrics or not self._metrics[metric_name]:
            return 0.0
        return sum(self._metrics[metric_name]) / len(self._metrics[metric_name])

    def get_total(self, metric_name: str) -> float:
        """Get total value for a metric."""
        if metric_name not in self._metrics:
            return 0.0
        return sum(self._metrics[metric_name])

    def get_count(self, metric_name: str) -> int:
        """Get count of recorded values for a metric."""
        if metric_name not in self._metrics:
            return 0
        return len(self._metrics[metric_name])

    def reset(self) -> None:
        """Reset all metrics."""
        self._metrics.clear()

    def get_all_metrics(self) -> dict[str, dict[str, float]]:
        """Get all metrics with aggregations."""
        result = {}
        for metric_name in self._metrics:
            result[metric_name] = {
                "total": self.get_total(metric_name),
                "average": self.get_average(metric_name),
                "count": self.get_count(metric_name),
            }
        return result


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    return _metrics_collector
