"""Domain models - pure data structures with no dependencies."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class BatchMetadata:
    """Metadata for a batch processing run."""

    batch_id: str
    source: str
    ingestion_time: datetime
    record_count: int
    version: str = "v1"  # semantic or numeric version
    checksum: Optional[str] = None
    layer: Optional[str] = None  # bronze, silver, gold

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "batch_id": self.batch_id,
            "source": self.source,
            "ingestion_time": self.ingestion_time.isoformat(),
            "record_count": self.record_count,
            "version": self.version,
            "checksum": self.checksum,
            "layer": self.layer,
        }


@dataclass
class DataRecord:
    """Generic data record for domain-agnostic operations."""

    timestamp: datetime
    entity_id: str
    value: float
    metadata: Optional[dict] = None


@dataclass
class ValidationResult:
    """Result of data validation."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    records_validated: int
    records_failed: int

    @property
    def success_rate(self) -> float:
        """Calculate validation success rate."""
        if self.records_validated == 0:
            return 0.0
        return (self.records_validated - self.records_failed) / self.records_validated
