"""API response schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    database_connected: bool = Field(..., description="Database connection status")
    storage_accessible: bool = Field(..., description="Storage accessibility status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Check timestamp")


class MetricsV1(BaseModel):
    """Metrics response v1.
    
    Future versions (MetricsV2) can add:
    - Detailed lineage information
    - Performance breakdown by stage
    - Data quality scores
    """

    total_records: int = Field(..., description="Total records in gold layer")
    entity_count: int = Field(..., description="Number of unique entities")
    date_range: Optional[dict[str, str]] = Field(None, description="Data date range")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")


# Alias for backward compatibility
MetricsResponse = MetricsV1


class ErrorResponse(BaseModel):
    """Error response."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")


class GoldDataResponse(BaseModel):
    """Gold layer data response."""

    data: list[dict[str, Any]] = Field(..., description="Gold layer records")
    count: int = Field(..., description="Number of records returned")
    total_available: int = Field(..., description="Total records available")


class BatchJobRequest(BaseModel):
    """Batch job execution request."""

    source: str = Field(default="api", description="Data source identifier")


class BatchJobResponse(BaseModel):
    """Batch job execution response."""

    batch_id: str = Field(..., description="Batch execution ID")
    status: str = Field(..., description="Execution status")
    message: str = Field(..., description="Status message")
