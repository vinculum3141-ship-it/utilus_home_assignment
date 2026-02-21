"""Application metrics - data structures for tracking performance."""

from dataclasses import dataclass


@dataclass
class PipelineMetrics:
    """Metrics for a pipeline execution."""

    records_in: int
    records_out: int
    duration_seconds: float
    errors: int

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.records_in == 0:
            return 0.0
        return (self.records_out / self.records_in) * 100

    @property
    def throughput(self) -> float:
        """Calculate throughput (records per second)."""
        if self.duration_seconds == 0:
            return 0.0
        return self.records_in / self.duration_seconds

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "records_in": self.records_in,
            "records_out": self.records_out,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors,
            "success_rate": self.success_rate,
            "throughput": self.throughput,
        }
