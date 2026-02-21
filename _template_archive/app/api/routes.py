"""API routes - thin HTTP interface."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_repository
from app.api.schemas import GoldDataResponse, HealthResponse, MetricsResponse
from app.infrastructure.monitoring import SystemHealth
from app.infrastructure.repositories.base import BaseRepository

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(repository: BaseRepository = Depends(get_repository)) -> HealthResponse:
    """
    Health check endpoint.

    Checks:
    - Database connectivity
    - Storage accessibility
    """
    # Check repository health
    storage_ok = repository.health_check()

    # Check database (basic check via repository)
    db_ok = storage_ok  # Simplified - repository check covers both

    status = "healthy" if (db_ok and storage_ok) else "unhealthy"

    return HealthResponse(
        status=status,
        database_connected=db_ok,
        storage_accessible=storage_ok,
        timestamp=datetime.now(),
    )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(repository: BaseRepository = Depends(get_repository)) -> MetricsResponse:
    """
    Get aggregated metrics from gold layer.

    Returns:
        Business-level metrics
    """
    try:
        gold_df = repository.read_gold()

        # Handle empty data
        if hasattr(gold_df, "__len__"):  # pandas
            if len(gold_df) == 0:
                return MetricsResponse(
                    total_records=0,
                    entity_count=0,
                    date_range=None,
                    last_updated=None,
                )
            
            total_records = len(gold_df)
            entity_count = gold_df["entity_id"].nunique() if "entity_id" in gold_df.columns else 0
            
            date_range = None
            if "date" in gold_df.columns:
                date_range = {
                    "start": str(gold_df["date"].min()),
                    "end": str(gold_df["date"].max()),
                }
            
            last_updated = None
            if "aggregated_at" in gold_df.columns:
                last_updated = gold_df["aggregated_at"].max()

        else:  # Spark
            if gold_df.count() == 0:
                return MetricsResponse(
                    total_records=0,
                    entity_count=0,
                    date_range=None,
                    last_updated=None,
                )
            
            total_records = gold_df.count()
            entity_count = gold_df.select("entity_id").distinct().count() if "entity_id" in gold_df.columns else 0
            date_range = None
            last_updated = None

        return MetricsResponse(
            total_records=total_records,
            entity_count=entity_count,
            date_range=date_range,
            last_updated=last_updated,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve metrics: {str(e)}")


@router.get("/gold", response_model=GoldDataResponse)
async def get_gold_data(
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    repository: BaseRepository = Depends(get_repository),
) -> GoldDataResponse:
    """
    Query gold layer data.

    Args:
        limit: Maximum number of records to return

    Returns:
        Gold layer data
    """
    try:
        gold_df = repository.read_gold()

        # Handle pandas vs Spark
        if hasattr(gold_df, "to_dict"):  # pandas
            total_available = len(gold_df)
            
            # Limit results
            limited_df = gold_df.head(limit)
            
            # Convert to dict
            data = limited_df.to_dict(orient="records")
            
            return GoldDataResponse(
                data=data,
                count=len(data),
                total_available=total_available,
            )

        else:  # Spark
            total_available = gold_df.count()
            
            # Limit results
            limited_df = gold_df.limit(limit)
            
            # Convert to list of dicts
            data = [row.asDict() for row in limited_df.collect()]
            
            return GoldDataResponse(
                data=data,
                count=len(data),
                total_available=total_available,
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve gold data: {str(e)}")


@router.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "service": "Energy Data Platform",
        "version": "0.1.0",
        "status": "running",
    }
