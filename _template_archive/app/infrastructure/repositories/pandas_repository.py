"""Pandas-based repository for local execution."""

import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.domain.exceptions import DataIntegrityError, RepositoryError
from app.domain.models import BatchMetadata
from app.infrastructure.logging import get_logger
from app.infrastructure.repositories.base import BaseRepository
from app.infrastructure.resilience import with_resilience
from app.infrastructure.settings import Settings

logger = get_logger(__name__)


class PandasRepository(BaseRepository):
    """Repository implementation using pandas for local storage."""

    def __init__(self, settings: Settings):
        """
        Initialize pandas repository.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create storage directories if they don't exist."""
        Path(self.settings.bronze_full_path).mkdir(parents=True, exist_ok=True)
        Path(self.settings.silver_full_path).mkdir(parents=True, exist_ok=True)
        Path(self.settings.gold_full_path).mkdir(parents=True, exist_ok=True)
        Path(self.settings.metadata_full_path).mkdir(parents=True, exist_ok=True)

    def read_bronze(self) -> pd.DataFrame:
        """Read bronze data from parquet files."""
        bronze_path = Path(self.settings.bronze_full_path)
        parquet_files = list(bronze_path.glob("*.parquet"))

        if not parquet_files:
            # Return empty DataFrame with expected schema if no files exist
            return pd.DataFrame(columns=["timestamp", "entity_id", "value"])

        # Read all parquet files and concatenate
        dfs = [pd.read_parquet(f) for f in parquet_files]
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    def _checksum_exists(self, checksum: str, layer: str) -> bool:
        """Check if data with this checksum already exists.
        
        Production idempotency check to prevent duplicate writes.
        
        Args:
            checksum: SHA256 checksum of data
            layer: Data layer (silver/gold)
        
        Returns:
            True if checksum exists (duplicate data)
        """
        if not checksum:
            return False
        
        metadata_path = Path(self.settings.metadata_full_path)
        if not metadata_path.exists():
            return False
        
        # Check all metadata files for this checksum
        for metadata_file in metadata_path.glob("*_metadata.json"):
            try:
                with open(metadata_file) as f:
                    metadata = json.load(f)
                    if metadata.get("checksum") == checksum and metadata.get("layer") == layer:
                        logger.info(
                            "duplicate_data_detected",
                            checksum=checksum,
                            layer=layer,
                            existing_batch=metadata.get("batch_id"),
                        )
                        return True
            except Exception as e:
                logger.warning("metadata_check_failed", file=str(metadata_file), error=str(e))
                continue
        
        return False

    @with_resilience(circuit_breaker_name="pandas_storage", max_retry_attempts=3)
    def write_silver(self, df: pd.DataFrame, metadata: BatchMetadata) -> None:
        """Write silver data to parquet with idempotency check.
        
        Production features:
        - Idempotent: Won't write duplicate data (checked by checksum)
        - Resilient: Retries on transient failures
        - Circuit breaker: Prevents cascade failures
        """
        # Idempotency check
        if metadata.checksum and self._checksum_exists(metadata.checksum, "silver"):
            logger.info(
                "skipping_duplicate_write",
                layer="silver",
                checksum=metadata.checksum,
                batch_id=metadata.batch_id,
            )
            raise DataIntegrityError(
                f"Data with checksum {metadata.checksum} already exists in silver layer. "
                "This indicates duplicate processing attempt."
            )
        
        try:
            # Support optional versioned folders
            base_path = Path(self.settings.silver_full_path)
            if hasattr(metadata, 'version') and metadata.version:
                version_path = base_path / metadata.version
                version_path.mkdir(parents=True, exist_ok=True)
                output_path = version_path / f"{metadata.batch_id}.parquet"
            else:
                output_path = base_path / f"{metadata.batch_id}.parquet"
            df.to_parquet(output_path, index=False)
            
            logger.info(
                "silver_write_successful",
                batch_id=metadata.batch_id,
                checksum=metadata.checksum,
                path=str(output_path),
            )
        except Exception as e:
            logger.error(
                "silver_write_failed",
                batch_id=metadata.batch_id,
                error=str(e),
                exc_info=True,
            )
            raise RepositoryError(f"Failed to write silver data: {e}")

    def read_silver(self) -> pd.DataFrame:
        """Read silver data from parquet files."""
        silver_path = Path(self.settings.silver_full_path)
        parquet_files = list(silver_path.glob("*.parquet"))

        if not parquet_files:
            return pd.DataFrame()

        dfs = [pd.read_parquet(f) for f in parquet_files]
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    @with_resilience(circuit_breaker_name="pandas_storage", max_retry_attempts=3)
    def write_gold(self, df: pd.DataFrame, metadata: BatchMetadata) -> None:
        """Write gold data to parquet with idempotency check.
        
        Production features:
        - Idempotent: Won't write duplicate data (checked by checksum)
        - Resilient: Retries on transient failures
        - Circuit breaker: Prevents cascade failures
        """
        # Idempotency check
        if metadata.checksum and self._checksum_exists(metadata.checksum, "gold"):
            logger.info(
                "skipping_duplicate_write",
                layer="gold",
                checksum=metadata.checksum,
                batch_id=metadata.batch_id,
            )
            raise DataIntegrityError(
                f"Data with checksum {metadata.checksum} already exists in gold layer. "
                "This indicates duplicate processing attempt."
            )
        
        try:
            # Support optional versioned folders
            base_path = Path(self.settings.gold_full_path)
            if hasattr(metadata, 'version') and metadata.version:
                version_path = base_path / metadata.version
                version_path.mkdir(parents=True, exist_ok=True)
                output_path = version_path / f"{metadata.batch_id}.parquet"
            else:
                output_path = base_path / f"{metadata.batch_id}.parquet"
            df.to_parquet(output_path, index=False)
            
            logger.info(
                "gold_write_successful",
                batch_id=metadata.batch_id,
                checksum=metadata.checksum,
                path=str(output_path),
            )
        except Exception as e:
            logger.error(
                "gold_write_failed",
                batch_id=metadata.batch_id,
                error=str(e),
                exc_info=True,
            )
            raise RepositoryError(f"Failed to write gold data: {e}")

    def read_gold(self) -> pd.DataFrame:
        """Read gold data from parquet files."""
        gold_path = Path(self.settings.gold_full_path)
        parquet_files = list(gold_path.glob("*.parquet"))

        if not parquet_files:
            return pd.DataFrame()

        dfs = [pd.read_parquet(f) for f in parquet_files]
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    @with_resilience(circuit_breaker_name="pandas_storage", max_retry_attempts=3)
    def save_metadata(self, metadata: BatchMetadata) -> None:
        """Save metadata to JSON file with resilience."""
        try:
            metadata_path = (
                Path(self.settings.metadata_full_path) / f"{metadata.batch_id}_metadata.json"
            )
            with open(metadata_path, "w") as f:
                json.dump(metadata.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(
                "metadata_write_failed",
                batch_id=metadata.batch_id,
                error=str(e),
            )
            raise RepositoryError(f"Failed to save metadata: {e}")

    def health_check(self) -> bool:
        """Check if storage is accessible."""
        try:
            self._ensure_directories()
            # Try to write and read a test file
            test_path = Path(self.settings.storage_path) / ".health_check"
            test_path.write_text("ok")
            content = test_path.read_text()
            test_path.unlink()
            return content == "ok"
        except Exception:
            return False
